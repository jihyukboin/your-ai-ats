import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.planner_agent import run_planner

TODAY = date(2026, 11, 18)
REQUEST = "내일 오후 2시부터 2시 10분까지 Python 이슈 읽기 계획"


class PlannerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.events, self.calls = [], []
        self.lengths = [5000, None, 300, 900]

    async def invoke(self, name, args):
        self.calls.append((name, args))
        if name == "search_candidates":
            page = args["page"]
            numbers = {1: [1, 2], 2: [2, 3], 3: [4]}[page]
            data = dict(items=[dict(id=f"team/demo#{i}", name=f"Issue {i}", url=f"https://github.com/team/demo/issues/{i}")
                               for i in numbers], has_more=page < 3, note="조회 기준일과 계획일이 다릅니다.")
        elif name == "candidate_detail":
            num = int(args["id"].split("#")[1])
            data = dict(id=args["id"], name=f"Issue {num}", url=f"https://github.com/team/demo/issues/{num}",
                        body_chars=self.lengths[num-1])
        elif name == "search_resources":
            return {"ok": False, "error": {"code": "AUTH_ERROR", "message": "서버의 API 키 설정을 확인하세요."}}
        else:
            self.fail(name)
        return {"ok": True, "data": data}

    async def run_request(self, request, memory=None, **options):
        return await run_planner(request, memory, self.events.append, invoke=self.invoke, today=TODAY, **options)

    async def test_replan_and_source_calculation(self):
        result = await self.run_request(REQUEST)
        self.assertEqual((result["status"], result["replans"]), ("recommended", 1))
        self.assertEqual(result["conditions"], dict(date="2026-11-19", start_time="14:00", end_time="14:10", language="Python"))
        proposal = result["proposal"]
        self.assertEqual(proposal["end_time"], "14:06")
        self.assertIn("14:04", proposal["notes"])
        self.assertIn("300", proposal["notes"])
        self.assertIn("가용 10분 초과", result["excluded"][0]["reason"])
        self.assertIn("미확인", result["excluded"][1]["reason"])
        self.assertIn("AUTH_ERROR", result["answer"])
        self.assertIn("조회 기준일", result["answer"])
        self.assertEqual(self.calls.count(("candidate_detail", {"id": "team/demo#2"})), 1)
        self.assertEqual(self.calls[0][1]["reference_date"], "2026-11-19")
        self.assertEqual(sum(name == "search_resources" for name, _ in self.calls), 1)
        requests = [e for e in self.events if e["type"] == "tool_request"]
        responses = [e for e in self.events if e["type"] == "tool_response"]
        self.assertEqual([e["data"]["tool"] for e in requests], [e["data"]["tool"] for e in responses])
        self.assertTrue(all(e["data"]["duration_ms"] >= 0 for e in responses))
        self.assertEqual(sum(e["type"] == "replan" for e in self.events), 1)
        self.assertEqual([e["stage"] for e in self.events if e["type"] == "stage_start"],
                         [e["stage"] for e in self.events if e["type"] == "stage_end"])

    async def test_cap_and_follow_up(self):
        first = await self.run_request(REQUEST, max_replans=0)
        self.assertEqual(first["status"], "no_match")
        self.assertIn("상한 0회", first["answer"])
        second = await self.run_request("같은 조건에서 마감만 15:00까지", first["memory"])
        self.assertEqual(second["conditions"], {**first["conditions"], "end_time": "15:00"})
        self.assertEqual(second["proposal"]["title"], "Issue 1")
        third = await self.run_request("같은 날 다른 이슈로", second["memory"])
        self.assertEqual(third["proposal"]["title"], "Issue 3")
        self.assertEqual(third["conditions"], second["conditions"])

    async def test_only_changed_clock_is_updated(self):
        first = await self.run_request("오늘 14:00부터 15:00까지 Python 이슈 읽기 계획")
        for followup, key, value in (
            ("같은 조건에서 종료만 14시 10분으로 바꿔줘", "end_time", "14:10"),
            ("마감만 14시 20분으로", "end_time", "14:20"),
            ("시작만 14시 05분으로", "start_time", "14:05"),
        ):
            with self.subTest(followup=followup):
                updated = await self.run_request(followup, first["memory"])
                self.assertEqual(updated["conditions"], {**first["conditions"], key: value})

    async def test_required_conditions_and_no_tool(self):
        result = await self.run_request("파이썬 이슈")
        self.assertEqual(result["status"], "clarify")
        self.assertIn("날짜", result["answer"])
        self.assertEqual(result["conditions"], {"language": "Python"})
        for msg in ["안녕하세요!", "사용법을 알려줘"]:
            self.assertEqual((await self.run_request(msg))["status"], "help")
        malformed = await self.run_request("2026-02-31 25:00부터 Python 이슈 계획")
        self.assertEqual(malformed["status"], "clarify")
        self.assertEqual(self.calls, [])

    async def test_model_routes_only_to_requested_resource_tool(self):
        with patch("app.planner_intent.model_intent", AsyncMock(return_value=("search_resources", "Python", "참고 질문 요청"))):
            result = await self.run_request("인기 토론을 읽으며 공부하고 싶어요")
        self.assertEqual([name for name, args in self.calls], ["search_resources"])
        decision = next(e["data"] for e in self.events if e["type"] == "decision")
        self.assertEqual((decision["selected_tool"], decision["reason"]), ("search_resources", "참고 질문 요청"))
        self.assertIn("AUTH_ERROR", result["answer"])

    async def test_duration_persists_during_clarification(self):
        first = await self.run_request("파이썬 이슈를 내일 10분 동안 볼래")
        self.assertEqual(first["status"], "clarify")
        second = await self.run_request("오후 2시부터", first["memory"])
        self.assertEqual(second["conditions"]["end_time"], "14:10")
        self.assertEqual(second["status"], "recommended")
