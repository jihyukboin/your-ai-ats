"""LangGraph for scheduling a bounded first review of a public open-source issue."""
import json
import math
import os
import re
from datetime import datetime, timezone
from time import perf_counter
from typing import TypedDict
from zoneinfo import ZoneInfo

from langgraph.graph import END, START, StateGraph

from . import planner_intent, planner_tools
from .planner_intent import clock, minutes

READING_RATE = 300
NOTES_MINUTES = 5
FIELDS = {"date": "검토 날짜", "start_time": "시작 시각", "end_time": "마감 시각", "language": "프로그래밍 언어"}
HELP = "원하는 언어와 검토 날짜, 시작·마감 시각을 알려 주세요. 예를 들어 ‘내일 14:00부터 15:00까지 Python 이슈 읽기 계획을 짜줘’라고 요청할 수 있어요. ‘Python 참고 자료’만 따로 조회할 수도 있어요."


class State(TypedDict, total=False):
    message: str
    memory: dict
    conditions: dict
    intent: str
    status: str
    reason: str
    page: int
    replans: int
    tasks: list
    cache: dict
    page_result: dict
    details: list
    resources: list
    excluded: list
    omitted_ids: list
    warnings: list
    sources: list
    proposal: dict | None
    selection: dict
    retry: bool
    answer: str


def graph_for(*, invoke, emit, today, max_replans):
    def publish(kind, stage, **data):
        if emit:
            emit({"type": kind, "stage": stage, "data": data,
                  "timestamp": datetime.now(timezone.utc).isoformat()})

    async def analyze(state):
        message = state["message"]
        memory = state["memory"]
        previous = memory.get("conditions", {})
        if re.search(r"처음부터|초기화|새로운 계획|새 계획", message):
            previous = {}
        try:
            changes = planner_intent.extract(message, today)
        except ValueError:
            return dict(conditions=previous, intent="clarify", status="clarify",
                        reason="유효한 날짜와 같은 날의 시작·마감 시각을 입력해 주세요.")
        conditions = {**previous, **changes}
        if "end_time" in changes and "duration" not in changes:
            conditions.pop("duration", None)
        duration = conditions.get("duration")
        if duration is not None and conditions.get("start_time"):
            deadline = minutes(conditions["start_time"]) + duration
            if deadline >= 1440 or not duration:
                return dict(conditions=previous, intent="clarify", status="clarify",
                            reason="검토 시간은 양수이며 종료 시각은 같은 날이어야 합니다.")
            if not changes.get("end_time") or minutes(changes["end_time"]) > deadline:
                conditions["end_time"] = clock(deadline)
        decision, reason = planner_intent.rule_intent(message, changes, previous)
        method, selected_tool = "rule", None
        if decision is None:
            selected_tool, language, reason = await planner_intent.model_intent(message, previous)
            method = "model_router"
            decision = {"search_candidates": "plan", "search_resources": "resources"}.get(selected_tool, "clarify")
            if language:
                conditions["language"] = language
        publish("decision", "analyze", method=method, intent=decision, reason=reason,
                selected_tool=selected_tool, changes={k: v for k, v in conditions.items() if previous.get(k) != v})
        status = ""
        if decision == "help":
            status = "help"
        elif decision == "clarify":
            status = "clarify"
        else:
            required = list(FIELDS) if decision == "plan" else ["language"]
            missing = [FIELDS[field] for field in required if not conditions.get(field)]
            if missing:
                status, reason = "clarify", ", ".join(missing) + "을(를) 알려 주세요."
            elif decision == "plan" and conditions["end_time"] <= conditions["start_time"]:
                status, reason = "clarify", "같은 날 마감 시각이 시작 시각보다 늦어야 해요. 시간을 다시 알려 주세요."
        omit = []
        if re.search(r"다른\s*(후보|이슈|걸|것)", message) and previous:
            omit = list(memory.get("omitted_ids", []))
            if memory.get("selected_id"):
                omit = list(dict.fromkeys([*omit, memory["selected_id"]]))
        return dict(conditions=conditions, intent=decision, status=status, reason=reason, omitted_ids=omit)

    async def plan(state):
        c = state["conditions"]
        tasks = []
        if state["intent"] == "plan":
            tasks.extend([{"tool": "search_candidates", "args": {"language": c["language"], "page": state["page"], "reference_date": c["date"]}},
                          {"tool": "candidate_detail", "from": "search_candidates.items[].id"}])
        if state["page"] == 1:
            tasks.append({"tool": "search_resources", "args": {"language": c["language"]}})
        publish("plan", "plan", tasks=tasks, page=state["page"])
        return {"tasks": tasks}

    async def execute(state):
        cache = dict(state["cache"])
        warnings = list(state["warnings"])

        async def call(tool, args):
            key = json.dumps([tool, args], sort_keys=True)
            if key not in cache:
                publish("tool_request", "execute", tool=tool, arguments=args)
                start = perf_counter()
                result = await invoke(tool, args)
                elapsed_ms = round((perf_counter() - start) * 1000, 2)
                publish("tool_response", "execute", tool=tool, ok=result["ok"], result=result, duration_ms=elapsed_ms)
                cache[key] = result
            result = cache[key]
            if not result["ok"]:
                warning = f"{tool} · {result['error']['code']} · {result['error']['message']}"
                if warning not in warnings:
                    warnings.append(warning)
            return result

        details, page, resources = [], {}, state["resources"]
        for task in state["tasks"]:
            name = task["tool"]
            if name == "search_candidates":
                result = await call(name, task["args"])
                page = result.get("data", {})
            elif name == "candidate_detail":
                for candidate in page.get("items", []):
                    if candidate["id"] in state["omitted_ids"]:
                        details.append({"candidate": candidate, "reason": "이전 추천을 제외해 달라는 요청"})
                        continue
                    result = await call(name, {"id": candidate["id"]})
                    if result["ok"]:
                        details.append({"candidate": candidate, "issue": result["data"]})
                    else:
                        details.append({"candidate": candidate, "reason": result["error"]["message"],
                                        "error": result["error"]["code"]})
            elif name == "search_resources":
                result = await call(name, task["args"])
                resources = result.get("data", {}).get("items", [])
        note = page.get("note")
        if note and note not in warnings:
            warnings.append(note)
        return dict(cache=cache, warnings=warnings, page_result=page, details=details, resources=resources)

    async def judge(state):
        if state["intent"] == "resources":
            status = "recommended" if state["resources"] else "no_match"
            return dict(status=status, retry=False, reason="언어별 참고 질문 검색 결과입니다.")
        conditions = state["conditions"]
        start, deadline = minutes(conditions["start_time"]), minutes(conditions["end_time"])
        available = deadline - start
        excluded = {row["id"]: row for row in state["excluded"]}
        eligible = []
        for record in state["details"]:
            candidate = record["candidate"]
            issue = record.get("issue", {})
            chars = issue.get("body_chars")
            reason = record.get("reason")
            if not reason:
                if not chars:
                    reason = "본문 길이 미확인으로 검토 시간 계산 불가"
                else:
                    needed = math.ceil(chars / READING_RATE) + NOTES_MINUTES
                    if needed > available:
                        reason = f"검토 {needed}분 예상, 가용 {available}분 초과"
                    else:
                        eligible.append((needed, issue))
            if reason:
                excluded[candidate["id"]] = {**candidate, "reason": reason}
        common = {"excluded": list(excluded.values()), "retry": False}
        if eligible:
            needed, issue = min(eligible, key=lambda pair: pair[0])
            latest = clock(deadline - needed)
            notes = (f"본문 {issue['body_chars']}자 ÷ 분당 {READING_RATE}자(올림) + 메모 {NOTES_MINUTES}분"
                     f" = 예상 {needed}분. 마감 {conditions['end_time']} 기준 늦어도 {latest} 시작.")
            proposal = dict(title=issue["name"], date=conditions["date"], start_time=conditions["start_time"],
                            end_time=clock(start + needed), url=issue["url"], notes=notes)
            return {**common, "status": "recommended", "proposal": proposal, "selection": issue,
                    "reason": f"조회한 페이지에서 가용 {available}분 안에 검토할 수 있는 후보 중 예상 시간이 가장 짧습니다."}
        if not state["page_result"]:
            reason = "후보 목록을 확보하지 못했습니다."
        elif any(record.get("error") in {"AUTH_ERROR", "RATE_LIMIT", "UNAVAILABLE", "UPSTREAM_ERROR"}
                 for record in state["details"]):
            reason = "상세 조회 제공기관의 오류로 추가 페이지 조회를 중단했습니다."
        elif not state["page_result"].get("has_more"):
            reason = "마지막 페이지까지 확인했지만 제약을 만족하는 후보가 없습니다."
        elif state["replans"] >= max_replans:
            reason = f"재계획 상한 {max_replans}회에 도달했습니다. 검토 시간을 늘리거나 언어를 변경해 주세요."
        else:
            reason = "현재 페이지에 조건을 만족하는 후보가 없어 같은 언어의 다음 페이지를 확인합니다."
            publish("replan", "judge", reason=reason, from_page=state["page"], to_page=state["page"]+1,
                    count=state["replans"]+1, limit=max_replans)
            return {**common, "retry": True, "replans": state["replans"]+1, "page": state["page"]+1, "reason": reason}
        return {**common, "status": "no_match", "reason": reason}

    async def respond(state):
        proposal, issue = state["proposal"], state.get("selection", {})
        sources = []
        if proposal:
            lines = [f"{proposal['date']} {proposal['start_time']}~{proposal['end_time']}에 "
                     f"{proposal['title']} ({issue['id']}) 본문 검토를 추천합니다.", state["reason"], proposal["notes"],
                     "예상 시간에는 댓글 읽기와 코드 수정이 포함되지 않습니다."]
            sources.append({"name": issue["id"], "url": issue["url"]})
        elif state["status"] == "help":
            lines = [HELP]
        else:
            lines = [state["reason"]]
        for r in state["resources"]:
            lines.append(f"언어 참고 자료 · {r['name']} ({r['author']}, {r['license']})")
            sources.append(r)
        for item in state["excluded"]:
            lines.append(f"제외 · {item['id']} · {item['reason']}")
        lines.extend(state["warnings"])
        answer = "\n".join(lines)
        memory = dict(conditions=state["conditions"], last_request=state["message"],
                      last_answer=answer[:800], selected_id=issue.get("id") or state["memory"].get("selected_id"),
                      omitted_ids=state.get("omitted_ids", [])[-40:])
        return dict(answer=answer, sources=sources, memory=memory)

    graph = StateGraph(State)
    for name, fn in [("analyze", analyze), ("plan", plan), ("execute", execute), ("judge", judge), ("respond", respond)]:
        def observe(name, fn):
            async def wrapped(state):
                publish("stage_start", name)
                update = await fn(state)
                summary = {key: update[key] for key in ("status", "intent", "reason", "conditions", "retry") if key in update}
                publish("stage_end", name, **summary)
                return update
            return wrapped
        graph.add_node(name, observe(name, fn))
    graph.add_edge(START, "analyze")
    graph.add_conditional_edges("analyze", lambda s: "respond" if s["status"] else "plan", ["respond", "plan"])
    graph.add_edge("plan", "execute")
    graph.add_edge("execute", "judge")
    graph.add_conditional_edges("judge", lambda s: "plan" if s["retry"] else "respond", ["plan", "respond"])
    graph.add_edge("respond", END)
    return graph.compile()


async def run_planner(message, memory=None, emit=None, *, invoke=None, today=None, max_replans=None):
    if max_replans is None:
        max_replans = int(os.getenv("PLANNER_MAX_REPLANS", "2"))
    graph = graph_for(invoke=invoke or planner_tools.invoke_tool, emit=emit,
                      today=today or datetime.now(ZoneInfo("Asia/Seoul")).date(), max_replans=max(0, min(5, max_replans)))
    state = await graph.ainvoke(dict(message=message, memory=memory or {}, page=1, replans=0, cache={}, excluded=[],
                                     warnings=[], resources=[], proposal=None), config={"recursion_limit": 32})
    return {key: state[key] for key in ("answer", "status", "proposal", "memory", "conditions", "sources", "excluded", "replans")}
