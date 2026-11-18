"""Replay public Tool captures through the real HTTP app, isolated from the local DB."""
import argparse
import asyncio
from copy import deepcopy
from datetime import date
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

import httpx

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from app import database, planner_agent
from app.main import app

EVIDENCE = BACKEND.parent / "docs" / "evidence"
CAPTURE = json.loads((EVIDENCE / "live-tools.json").read_text())
DAY = CAPTURE["captured_at"][:10]
REQUEST = f"{DAY} 14:00부터 {{end}}까지 Python 이슈 읽기 계획을 짜줘"
SCENARIOS = [
    ("first", REQUEST.format(end="15:00"), "recommended", 0),
    ("followup", "같은 조건에서 종료만 14시 10분으로 바꿔줘", "recommended", 1),
    ("replan", REQUEST.format(end="14:10"), "recommended", 1),
    ("cap", REQUEST.format(end="14:02"), "no_match", 2),
    ("partial", REQUEST.format(end="15:00") + ". 참고자료도 알려줘", "recommended", 0),
    ("help", "사용법을 알려줘", "help", 0),
    ("missing_key", "어떻게 하지?", "clarify", 0),
    ("clarify", "Python 이슈 읽기 계획을 짜줘", "clarify", 0),
]
engine = planner_agent.run_planner


async def recorded_engine(message, memory, emit):
    async def replay(name, arguments):
        if name == "search_resources" and "참고자료도" in message:
            return {"ok": False, "error": {"code": "UNAVAILABLE", "message": "제공기관에 연결할 수 없습니다. 잠시 후 다시 시도하세요."}}
        for call in CAPTURE["calls"]:
            args = call["arguments"]
            if call["name"] != name:
                continue
            if name == "candidate_detail" and args["id"] != arguments.get("id"):
                continue
            if name == "search_candidates" and args["page"] != arguments.get("page", 1):
                continue
            if "language" in args and args["language"].casefold() != arguments.get("language", "").casefold():
                continue
            result = deepcopy(call["response"])
            if name == "search_candidates":
                requested = str(arguments.get("reference_date") or DAY)
                result["data"]["requested_date"] = requested
                if requested != DAY:
                    result["data"]["note"] = f"요청 기준일 {requested}, 실제 조회일 {DAY}의 열린 이슈를 사용했습니다."
            return result
        raise AssertionError(f"실측 데이터에 없는 호출: {name} {arguments}")

    if message == "어떻게 하지?":
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "GMS_API_KEY": ""}):
            return await engine(message, memory, emit, invoke=replay, today=date.fromisoformat(DAY), max_replans=2)
    return await engine(message, memory, emit, invoke=replay, today=date.fromisoformat(DAY), max_replans=2)


async def exercise(live):
    transcript = []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        for name, message, status, replans in SCENARIOS:
            started = perf_counter()
            session = "first" if name == "followup" else name
            response = await client.post("/api/planner/chat", json={"session_id": session, "message": message})
            response.raise_for_status()
            elapsed = round((perf_counter() - started) * 1000)
            result = response.json()
            assert result["status"] == status and result["replans"] == replans, (name, result["answer"])
            log = (await client.get("/api/planner/logs/" + session)).json()["runs"][-1]
            assert log["events"] == result["events"], name
            calls = [e["data"]["tool"] for e in result["events"] if e["type"] == "tool_request"]
            if name == "followup":
                assert result["conditions"] == {"date": DAY, "start_time": "14:00", "end_time": "14:10", "language": "Python"}
            if name == "missing_key":
                assert "키" in result["answer"]
            if name in ("help", "clarify", "missing_key"):
                assert not calls
            if name == "partial":
                assert "UNAVAILABLE" in json.dumps(result["events"])
            if name == "replan":
                (EVIDENCE / "replan-run.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n")
            transcript.append(dict(case=name, mode="captured_tools", message=message, status=status,
                                   replans=replans, tools=calls, elapsed_ms=elapsed, answer=result["answer"],
                                   stages=[e["stage"] for e in log["events"] if e["type"] == "stage_start"]))
        # Check the public service with the external providers enabled in the same isolated database.
        if live:
            with patch.object(planner_agent, "run_planner", engine):
                start = perf_counter()
                message = "내일 14:00부터 15:00까지 Python 이슈 읽기 계획을 짜줘"
                response = await client.post("/api/planner/chat", json={"session_id": "live", "message": message})
                response.raise_for_status()
                result = response.json()
                elapsed = round((perf_counter() - start) * 1000)
                calls = [e["data"]["tool"] for e in result["events"] if e["type"] == "tool_request"]
                live_sample = dict(case="live", mode="live_providers", message=message, status=result["status"],
                                       replans=result["replans"], tools=calls, elapsed_ms=elapsed, answer=result["answer"],
                                       events=result["events"])
                (EVIDENCE / "live-request.json").write_text(json.dumps(live_sample, ensure_ascii=False, indent=2) + "\n")
                assert result["proposal"] and len(calls) >= 3, result["answer"]
    (EVIDENCE / "scenarios.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2) + "\n")
    for run in transcript:
        print(run["case"], run["status"], run["replans"], run["elapsed_ms"], "ms")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="also call current external providers")
    parser.add_argument("--serve", type=int, metavar="PORT", help="serve captured data locally for UI verification")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temp, patch.object(planner_agent, "run_planner", recorded_engine):
        database.DATABASE_PATH = Path(temp) / "verification.sqlite3"
        database.initialize_database()
        if args.serve:
            import uvicorn
            uvicorn.run(app, host="127.0.0.1", port=args.serve)
        else:
            asyncio.run(exercise(args.live))
