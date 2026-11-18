import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import httpx

from app import database
from app.fit_evidence import Match, Matches, Requirement, Requirements
from app.main import app
from app.public_company_data import DART, NCS


class ResumeFitTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.enterContext(patch.object(database, "DATABASE_PATH", Path(temp.name) / "fit.db"))
        database.initialize_database()
        self.analysis_id = str(uuid4())
        self.url = "/api/companies/1/fit-analyses"
        self.body = dict(role="개발", analysis_id=self.analysis_id)
        self.job_url = "https://careers.example.org/jobs/12"
        with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
            db.execute("INSERT INTO companies(name) VALUES ('예시사'),('다른 회사')")
            analysis = dict(role="개발", status="done", text=f"필수: API 구현 [{self.job_url}]({self.job_url})",
                            sources=[self.job_url], stages=[
                                dict(source=DART, rows=[dict(hm_url="www.example.org")]),
                                dict(source=NCS, rows=[dict(COMPE_UNIT_NAME="테스트 작성")])])
            db.execute("INSERT INTO company_analyses VALUES(?,1,?)", (self.analysis_id, json.dumps(analysis)))
            resume = dict(id="기존", sections=[dict(id="2", title="프로젝트", tags=["API 구현 경험"])])
            db.execute("INSERT INTO resumes VALUES(?,?)", (resume["id"], json.dumps(resume)))

    async def asyncSetUp(self):
        self.client = await self.enterAsyncContext(httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                                                    base_url="http://test"))

    async def test_company_role_and_resume_prerequisites(self):
        response = await self.client.post("/api/companies/2/fit-analyses", json=self.body)
        self.assertEqual(response.status_code, 404)
        response = await self.client.post(self.url, json=self.body | dict(role="기획"))
        self.assertEqual(response.status_code, 409)
        with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
            db.execute("DELETE FROM resumes")
        self.assertEqual((await self.client.post(self.url, json=self.body)).status_code, 409)

    async def test_evidence_and_saved_snapshot(self):
        extracted = Requirements(items=[
            Requirement(text="테스트 작성", kind="required", source_index=0, quote="테스트 작성"),
            Requirement(text="API 구현", kind="required", source_index=1, quote="필수: API 구현")])
        assessed = Matches(items=[
            Match(requirement_index=0, verdict="direct", section_id="2", quote="없는 인용", reason="x", suggestion="x"),
            Match(requirement_index=1, verdict="direct", section_id="2", quote="API 구현 경험", reason="구현 경험", suggestion="")])
        with patch("app.resume_fit.generate", side_effect=[extracted, assessed]):
            response = await self.client.post(self.url, json=self.body)
        events = [json.loads(line) for line in response.iter_lines()]
        self.assertEqual([len(e["stages"]) for e in events], [1, 2, 3, 4, 4])
        end = events[-1]
        self.assertEqual(end["status"], "done")
        self.assertEqual(end["result"]["counts"]["general"]["direct"], 1)
        self.assertEqual(end["result"]["items"][0]["evidence"]["quote"], "없는 인용")
        self.assertEqual(end["result"]["counts"]["required"]["direct"], 1)
        self.assertEqual(end["result"]["items"][1]["evidence"]["section_title"], "프로젝트")
        with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
            db.execute("DELETE FROM resumes")
        self.assertEqual((await self.client.get(self.url)).json(), [end])
        self.assertEqual((await self.client.get(self.url + "/" + end["id"])).json(), end)
        self.assertEqual((await self.client.get("/api/companies/2/fit-analyses/" + end["id"])).status_code, 404)

    async def test_provider_failure_is_saved(self):
        with patch("app.resume_fit.generate", side_effect=httpx.ReadTimeout("timeout")):
            response = await self.client.post(self.url, json=self.body)
        end = json.loads(response.text.splitlines()[-1])
        self.assertEqual(end["status"], "failed")
        self.assertEqual(end["stages"][-1]["status"], "failed")
        self.assertEqual((await self.client.get(self.url)).json(), [end])
