"""Conversation, plans and read/delete-only execution log HTTP resources."""

import asyncio
from datetime import date as CalendarDate
from typing import Annotated, Any, Literal
from uuid import uuid4
from weakref import WeakValueDictionary

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, model_validator

from . import planner_agent, planner_store
from .planner_events import EventBus, LoggingAgent
from .planner_tools import tool_specs

router = APIRouter(prefix="/api/planner", tags=["플래너"])
SessionId = Annotated[str, StringConstraints(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")]
ClockTime = Annotated[str, StringConstraints(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")]
SessionStatus = Literal["recommended", "no_match", "clarify", "help", "error"]
_session_locks = WeakValueDictionary()


class PlanInput(BaseModel):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    date: CalendarDate
    start_time: ClockTime
    end_time: ClockTime
    notes: str = Field(default="", max_length=8000)
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def check_interval(self):
        if self.start_time >= self.end_time:
            raise ValueError("종료 시각은 같은 날의 시작 시각보다 늦어야 합니다.")
        return self


class Plan(PlanInput):
    id: str
    created_at: str
    updated_at: str


class PlanWriteResult(BaseModel):
    plan: Plan
    overlaps: list[Plan]


class ChatRequest(BaseModel):
    session_id: SessionId = Field(default_factory=lambda: str(uuid4()))
    message: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class Event(BaseModel):
    model_config = ConfigDict(extra="allow")
    session_id: str
    run_id: str
    seq: int
    at: str
    type: str
    stage: str
    data: dict[str, Any]


class Source(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    url: HttpUrl


class ChatResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    session_id: str
    run_id: str
    status: SessionStatus
    answer: str
    proposal: PlanInput | None
    conditions: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)
    excluded: list[dict[str, Any]] = Field(default_factory=list)
    replans: int = 0
    events: list[Event]


class LogSummary(BaseModel):
    session_id: str
    run_count: int
    event_count: int
    updated_at: str


class LoggedRun(BaseModel):
    run_id: str
    started_at: str
    message: str | None = None
    answer: str | None = None
    status: SessionStatus | None = None
    proposal: PlanInput | None = None
    sources: list[Source] = Field(default_factory=list)
    events: list[Event]


class SessionLog(BaseModel):
    session_id: str
    runs: list[LoggedRun]


@router.get("/tools")
def registered_tools() -> list[dict]:
    return tool_specs()


@router.post("/chat", response_model=ChatResult)
async def chat(body: ChatRequest):
    session_id = body.session_id
    lock = _session_locks.setdefault(session_id, asyncio.Lock())
    async with lock:
        run_id = str(uuid4())
        bus = EventBus(session_id, run_id)
        bus.subscribe(LoggingAgent())
        revision, previous = planner_store.load_memory(session_id)
        bus.publish({"type": "chat_started", "stage": "chat", "data": {"message": body.message}})
        try:
            output = await planner_agent.run_planner(body.message, previous, bus.publish)
        except Exception:
            bus.publish({"type": "chat_failed", "stage": "chat", "data": {"reason": "실행 중 오류"}})
            raise HTTPException(500, "플래너 실행을 마치지 못했습니다. 다시 시도해 주세요.") from None
        memory = output.pop("memory")
        if not planner_store.save_memory(session_id, revision, memory):
            bus.publish({"type": "chat_failed", "stage": "chat", "data": {"reason": "동시 대화 충돌"}})
            raise HTTPException(409, "같은 대화의 조건이 변경되었습니다. 다시 요청해 주세요.")
        bus.publish({"type": "chat_completed", "stage": "chat",
                     "data": {key: output[key] for key in ("answer", "status", "proposal", "sources") if key in output}})
        return {**output, "session_id": session_id, "run_id": run_id, "events": bus.events}


@router.get("/logs", response_model=list[LogSummary])
def list_logs():
    return planner_store.log_sessions()


@router.get("/logs/{session_id}", response_model=SessionLog)
def get_log(session_id: SessionId):
    log = planner_store.session_log(session_id)
    if log is None:
        raise HTTPException(404, "실행 로그가 없습니다.")
    return log


@router.delete("/logs/{session_id}", status_code=204)
def remove_log(session_id: SessionId):
    if not planner_store.delete_log(session_id):
        raise HTTPException(404, "실행 로그가 없습니다.")


@router.get("/plans", response_model=list[Plan])
def list_plans():
    return planner_store.list_plans()


@router.post("/plans", response_model=PlanWriteResult, status_code=201)
def create_plan(body: PlanInput):
    return planner_store.write_plan(body.model_dump(mode="json"))


@router.get("/plans/{plan_id}", response_model=Plan)
def get_plan(plan_id: str):
    plan = planner_store.get_plan(plan_id)
    if plan is None:
        raise HTTPException(404, "계획이 없습니다.")
    return plan


@router.put("/plans/{plan_id}", response_model=PlanWriteResult)
def replace_plan(plan_id: str, body: PlanInput):
    result = planner_store.write_plan(body.model_dump(mode="json"), plan_id)
    if result is None:
        raise HTTPException(404, "계획이 없습니다.")
    return result


@router.delete("/plans/{plan_id}", status_code=204)
def remove_plan(plan_id: str):
    if not planner_store.delete_plan(plan_id):
        raise HTTPException(404, "계획이 없습니다.")
