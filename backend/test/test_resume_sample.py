"""Run with uv run python -m unittest discover -s test (calls both providers)."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient

from app import database
from app.main import app


@unittest.skipUnless(os.getenv("RUN_RESUME_LIVE"), "requires provider credentials")
class ResumeSample(unittest.IsolatedAsyncioTestCase):
    async def test_sample(self):

        sample = Path(__file__).resolve().parents[2] / "secret" / "이력서_20261118.pdf"
        with tempfile.TemporaryDirectory() as temp, patch.object(database, "DATABASE_PATH", Path(temp) / "test.db"):
            database.initialize_database()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/resumes", files={"file": ("resume.pdf", sample.read_bytes())})
                events = [json.loads(line) for line in response.iter_lines()]
                self.assertNotIn("error", events[-1])
                result = events[-1]["result"]
                self.assertEqual(result["name"], "정지혁")
                self.assertEqual((await client.get(result["avatar"])).headers["content-type"], "image/jpeg")
                self.assertEqual((await client.get("/api/resumes/" + result["id"])).json(), result)
                self.assertIn("TOEIC", str(result["sections"]).upper())
                self.assertIn("희망", str(result["sections"]))
                section = result["sections"][0].copy()
                index = section.pop("id")
                section["title"] = "수정 테스트"
                response = await client.put(f"/api/resumes/{result['id']}/sections/{index}", json=section)
                self.assertEqual(response.status_code, 200)
                stored = (await client.get("/api/resumes/" + result["id"])).json()
                self.assertEqual(stored["sections"][0]["title"], "수정 테스트")
