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
from app.main import app


class CoverLetterTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.enterContext(patch.object(database, "DATABASE_PATH", Path(temp.name) / "letter.db"))
        database.initialize_database()
        self.fit_id = str(uuid4())
        self.url = "/api/companies/1/cover-letters"
        with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
            db.execute("INSERT INTO companies(name) VALUES ('예시사')")
            db.execute("INSERT INTO company_analyses VALUES('a',1,?)", (json.dumps(dict(text="사업 분석")),))
            db.execute("INSERT INTO resumes VALUES('r',?)", (json.dumps(dict(id="r", sections=[])),))
            fit = dict(id=self.fit_id, analysis_id="a", resume_id="r", role="개발", status="done", result=dict(items=[]))
            db.execute("INSERT INTO resume_fits VALUES(?,1,?)", (self.fit_id, json.dumps(fit)))

    async def asyncSetUp(self):
        self.client = await self.enterAsyncContext(httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                                                    base_url="http://test"))

    async def test_requires_finished_fit(self):
        response = await self.client.post(self.url, json=dict(fit_id=str(uuid4())))
        self.assertEqual(response.status_code, 409)

    async def test_strategy_is_streamed_and_saved(self):
        with patch("app.cover_letter.write", return_value="## 요약\n전략") as write:
            response = await self.client.post(self.url, json=dict(fit_id=self.fit_id, prompt="지원동기"))
        events = [json.loads(line) for line in response.iter_lines()]
        end = events[-1]
        self.assertEqual(end["status"], "done")
        self.assertEqual(end["text"], "## 요약\n전략")
        self.assertEqual([s["status"] for s in end["stages"]], ["done"] * 3)
        self.assertEqual(write.call_args.args[0]["question"], "지원동기")
        self.assertEqual((await self.client.get(self.url)).json(), [end])
