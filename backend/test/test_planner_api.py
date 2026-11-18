import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from app import database, planner_store
from app.main import app
from app.planner_events import EventBus, LoggingAgent

BASE = "/api/planner"


async def memory_probe(message, memory, emit):
    prior = memory.get("messages", [])
    emit({"type": "stage_enter", "stage": "analyze", "data": {"previous": prior}})
    emit({"type": "stage_exit", "stage": "analyze", "data": {}})
    await asyncio.sleep(0)
    return {"answer": " / ".join([*prior, message]), "status": "help", "proposal": None,
            "sources": [{"name": "자료", "url": "https://example.org/1", "author": "글쓴이"}],
            "memory": {"messages": [*prior, message]}}


class PlannerApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.enterContext(patch.object(database, "DATABASE_PATH", Path(temp.name) / "planner.db"))
        database.initialize_database()
        self.client = await self.enterAsyncContext(
            httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
        )

    async def test_overlapping_plan_is_saved_and_returned(self):
        data = dict(title="자료구조 이슈", date="2026-11-20", start_time="14:00", end_time="15:00",
                    notes="본문 검토", url="https://github.com/example/repo/issues/1")
        first = await self.client.post(BASE + "/plans", json=data)
        self.assertEqual(first.status_code, 201)
        plan = first.json()["plan"]
        self.assertEqual(first.json()["overlaps"], [])
        overlaps = await self.client.post(BASE + "/plans", json={**data, "start_time": "14:30"})
        self.assertEqual(overlaps.status_code, 201)
        self.assertEqual(overlaps.json()["overlaps"], [plan])
        self.assertEqual(len((await self.client.get(BASE + "/plans")).json()), 2)
        second = overlaps.json()["plan"]
        path = BASE + "/plans/" + second["id"]
        self.assertEqual((await self.client.get(path)).json(), second)
        adjacent = {**data, "start_time": "15:00", "end_time": "16:00", "title": "후속 검토"}
        updated = (await self.client.put(path, json=adjacent)).json()
        self.assertEqual(updated["overlaps"], [])
        self.assertEqual(updated["plan"]["created_at"], second["created_at"])
        self.assertEqual(updated["plan"]["title"], "후속 검토")
        self.assertEqual((await self.client.delete(path)).status_code, 204)
        self.assertEqual((await self.client.get(path)).status_code, 404)
        self.assertEqual((await self.client.get(BASE + "/plans")).json(), [plan])
        other_date = await self.client.post(BASE + "/plans", json={**data, "date": "2026-11-21"})
        self.assertEqual(other_date.json()["overlaps"], [])

    async def test_invalid_plan_inputs_and_missing_records(self):
        data = dict(title="검토", date="2026-11-20", start_time="14:00", end_time="15:00")
        for update in ({"title": " "}, {"date": "2026-02-31"}, {"start_time": "24:00"},
                       {"start_time": "15:00"}, {"url": "javascript:alert(1)"}):
            with self.subTest(update=update):
                self.assertEqual((await self.client.post(BASE + "/plans", json={**data, **update})).status_code, 422)
        self.assertEqual((await self.client.put(BASE + "/plans/missing", json=data)).status_code, 404)
        self.assertEqual((await self.client.delete(BASE + "/plans/missing")).status_code, 404)

    async def send(self, session_id, message):
        response = await self.client.post(BASE + "/chat", json={"session_id": session_id, "message": message})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_logs_preserve_events_order_and_isolate_sessions(self):
        with patch("app.planner_agent.run_planner", side_effect=memory_probe):
            await self.send("first", "원래 조건")
            isolated = await self.send("second", "다른 대화")
            reply = await self.send("first", "시간 변경")
            self.assertEqual(reply["answer"], "원래 조건 / 시간 변경")
            self.assertEqual(isolated["answer"], "다른 대화")
            self.assertNotIn("memory", reply)
            sessions = (await self.client.get(BASE + "/logs")).json()
            self.assertEqual({s["session_id"]: s["run_count"] for s in sessions}, {"first": 2, "second": 1})
            detail = (await self.client.get(BASE + "/logs/first")).json()
            self.assertEqual(detail["runs"][-1]["events"], reply["events"])
            self.assertEqual(detail["runs"][-1]["message"], "시간 변경")
            self.assertEqual(detail["runs"][-1]["answer"], reply["answer"])
            self.assertEqual(detail["runs"][-1]["sources"], reply["sources"])
            self.assertEqual([e["seq"] for e in reply["events"]], list(range(1, len(reply["events"]) + 1)))
            self.assertEqual((await self.client.put(BASE + "/logs/first", json={})).status_code, 405)
            self.assertEqual((await self.client.delete(BASE + "/logs/first")).status_code, 204)
            self.assertEqual((await self.client.get(BASE + "/logs/first")).status_code, 404)
            self.assertEqual((await self.client.get(BASE + "/logs/second")).status_code, 200)
            remembered = await self.send("first", "계속")
            self.assertEqual(remembered["answer"], "원래 조건 / 시간 변경 / 계속")

    async def test_unavailable_logging_agent_and_concurrent_followup(self):
        with (patch("app.planner_agent.run_planner", side_effect=memory_probe),
              patch.object(planner_store, "append_event", side_effect=OSError("unavailable")),
              self.assertLogs("app.planner_events", level="WARNING")):
            first, second = await asyncio.gather(self.send("same", "A"), self.send("same", "B"))
        self.assertEqual({first["answer"], second["answer"]}, {"A", "A / B"})
        self.assertEqual((await self.client.get(BASE + "/logs")).json(), [])

    def test_publisher_without_subscribers_and_event_snapshots(self):
        bus = EventBus("no-logger", "r")
        data = {"round": [1]}
        bus.publish({"type": "test", "stage": "judge", "data": data})
        data["round"].append(2)
        self.assertEqual(bus.events[0]["data"], {"round": [1]})
        self.assertEqual(planner_store.log_sessions(), [])

    def test_deletion_mid_run_cannot_restore_partial_log(self):
        bus = EventBus("s", "r")
        bus.subscribe(LoggingAgent())
        event = {"type": "stage_enter", "stage": "judge", "data": {}}
        bus.publish(event)
        self.assertTrue(planner_store.delete_log("s"))
        bus.publish(event)
        self.assertIsNone(planner_store.session_log("s"))
        subsequent = EventBus("s", "next")
        subsequent.subscribe(LoggingAgent())
        subsequent.publish(event)
        self.assertEqual(len(planner_store.session_log("s")["runs"][0]["events"]), 1)

    def test_stale_writer_cannot_overwrite_memory(self):
        self.assertTrue(planner_store.save_memory("s", 0, {"condition": "A"}))
        self.assertFalse(planner_store.save_memory("s", 0, {"condition": "B"}))
        self.assertTrue(planner_store.save_memory("s", 1, {"condition": "C"}))
        self.assertFalse(planner_store.save_memory("s", 1, {"condition": "D"}))
        self.assertEqual(planner_store.load_memory("s"), (2, {"condition": "C"}))
