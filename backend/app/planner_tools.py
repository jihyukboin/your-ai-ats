"""Public issue and reference lookups for the developer portfolio planner."""
import asyncio
import html
import os
import re
import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Annotated, Awaitable, Callable, Generic, Literal, TypeVar
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

GITHUB = "https://api.github.com"
STACK = "https://api.stackexchange.com/2.3"
PAGE_SIZE = 2
LANGUAGE = Annotated[str, Field(min_length=1, max_length=32, pattern=r"^[a-zA-Z][a-zA-Z0-9+#.\-]*$")]
ISSUE_ID = r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+#[1-9][0-9]{0,9}$"


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Topic(Input):
    language: LANGUAGE


class Search(Topic):
    page: int = Field(default=1, ge=1, le=500)
    reference_date: date | None = None


class IssueId(Input):
    id: str = Field(pattern=ISSUE_ID, max_length=180)


class Candidate(BaseModel):
    id: str
    name: str
    url: str


class CandidatePage(BaseModel):
    items: list[Candidate]
    page: int
    has_more: bool
    requested_date: str
    observed_date: str
    note: str


class Issue(Candidate):
    body_chars: int | None
    comments: int | None
    labels: list[str]


class Resource(BaseModel):
    name: str
    url: str
    author: str
    author_url: str
    license: str


class Resources(BaseModel):
    items: list[Resource]


T = TypeVar("T")


class Success(BaseModel, Generic[T]):
    ok: Literal[True]
    data: T


class ErrorDetails(BaseModel):
    code: str
    message: str


class Failure(BaseModel):
    ok: Literal[False]
    error: ErrorDetails


class ToolError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def issue_ref(value):
    if not re.fullmatch(ISSUE_ID, value):
        raise ValueError("invalid issue identifier")
    repo, number = value.rsplit("#", 1)
    if repo.split("/")[1] in {".", ".."}:
        raise ValueError("invalid repository name")
    return repo, number


def github_headers():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SSAFY-portfolio-planner"}
    if token := os.environ.get("PLANNER_GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


_github_wait = {}


async def github(client, path, **params):
    bucket = "search" if path == "/search/issues" else "core"
    if _github_wait.get(bucket, 0) > time.monotonic():
        raise ToolError("RATE_LIMIT", "GitHub 호출 한도가 복구될 때까지 기다려 주세요.")
    response = await client.get(GITHUB + path, headers=github_headers(), params=params)
    exhausted = response.headers.get("x-ratelimit-remaining") == "0"
    throttled = response.status_code == 429 or (response.status_code == 403 and (
        exhausted or "retry-after" in response.headers
        or "rate limit" in response.text.lower()
    ))
    if exhausted or throttled:
        delay = max(1, float(response.headers.get("retry-after", 0)),
                    float(response.headers.get("x-ratelimit-reset", 0)) - time.time() if exhausted else 0)
        if throttled and not exhausted and "retry-after" not in response.headers:
            delay = 60
        _github_wait[bucket] = time.monotonic() + delay
    if throttled:
        raise ToolError("RATE_LIMIT", "GitHub 호출 한도에 도달했습니다. 잠시 후 다시 시도하세요.")
    response.raise_for_status()
    return response.json()


async def search_candidates(client, args):
    language = args.language
    raw = await github(client, "/search/issues", q=f'is:public is:issue is:open label:"good first issue" language:{language}',
                       sort="created", order="desc", page=args.page, per_page=PAGE_SIZE)
    items = []
    for row in raw["items"]:
        repo_url = row["repository_url"]
        if not repo_url.startswith(GITHUB + "/repos/"):
            raise ValueError("invalid repository")
        issue_id = f"{repo_url.removeprefix(GITHUB + '/repos/')}#{row['number']}"
        repo, number = issue_ref(issue_id)
        items.append(Candidate(id=issue_id, name=row["title"], url=f"https://github.com/{repo}/issues/{number}"))
    if not items:
        raise ToolError("NO_RESULT", "선택한 언어와 페이지에서 열린 입문 이슈를 찾지 못했습니다.")
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    requested = args.reference_date or today
    notes = []
    if requested != today:
        notes.append(f"요청 기준일 {requested}의 상태는 확인할 수 없어 {today} 조회 시점의 열린 이슈를 사용했습니다.")
    if raw.get("incomplete_results"):
        notes.append("GitHub가 일부 검색 결과만 반환했습니다.")
    return CandidatePage(items=items, page=args.page, has_more=args.page * PAGE_SIZE < min(raw["total_count"], 1000),
                         observed_date=str(today), requested_date=str(requested), note=" ".join(notes))


async def candidate_detail(client, args):
    try:
        repo, number = issue_ref(args.id)
    except ValueError as exc:
        raise ToolError("INVALID_INPUT", "이슈 식별자는 owner/repository#번호 형식입니다.") from exc
    row = await github(client, f"/repos/{repo}/issues/{number}")
    if "pull_request" in row or row["state"] != "open":
        raise ToolError("NO_RESULT", "현재 열려 있는 이슈가 아닙니다.")
    labels = [label["name"] for label in row["labels"]]
    if "good first issue" not in {label.lower() for label in labels}:
        raise ToolError("NO_RESULT", "현재 입문용 라벨이 없는 이슈입니다.")
    body = row.get("body")
    return Issue(id=args.id, name=row["title"], url=f"https://github.com/{repo}/issues/{number}",
                 body_chars=len(body.strip()) if body and body.strip() else None, comments=row.get("comments"), labels=labels)


# Stack Exchange asks callers to reuse equivalent requests for at least a minute.
# Its backoff applies to this endpoint across all tags, including different sessions.
_resource_cache = {}
_resource_lock = asyncio.Lock()
_backoff_until = 0.0


async def search_resources(client, args):
    global _backoff_until
    tag = args.language.casefold()
    async with _resource_lock:
        now = time.monotonic()
        for expired in [key for key, (until, _) in _resource_cache.items() if until <= now]:
            del _resource_cache[expired]
        if tag in _resource_cache:
            resources = _resource_cache[tag][1]
        else:
            if now < _backoff_until:
                raise ToolError("RATE_LIMIT", "Stack Exchange가 추가 조회 대기를 요청했습니다.")
            response = await client.get(STACK + "/questions", params=dict(
                site="stackoverflow", tagged=tag, order="desc", sort="votes", pagesize=2))
            if response.status_code == 429:
                _backoff_until = now + int(response.headers.get("retry-after", 60))
                raise ToolError("RATE_LIMIT", "Stack Exchange 호출 한도에 도달했습니다.")
            if response.status_code == 400 and response.json().get("error_name") in ("throttle_violation", "temporarily_unavailable"):
                _backoff_until = now + 60
                raise ToolError("RATE_LIMIT", "Stack Exchange가 추가 조회 대기를 요청했습니다.")
            response.raise_for_status()
            raw = response.json()
            if raw.get("backoff"):
                _backoff_until = time.monotonic() + int(raw["backoff"])
            resources = []
            for row in raw["items"]:
                author = row.get("owner") or {}
                resources.append(Resource(name=html.unescape(row["title"]), url=row["link"],
                                          author=html.unescape(author.get("display_name", "Stack Overflow 사용자")),
                                          author_url=author.get("link", ""), license=row.get("content_license", "")))
            _resource_cache[tag] = (time.monotonic() + 60, resources)
        if not resources:
            raise ToolError("NO_RESULT", "이 언어 태그로 제공되는 Stack Overflow 참고 질문이 없습니다.")
        return Resources(items=resources)


@dataclass(frozen=True)
class Tool:
    description: str
    input: type[BaseModel]
    output: type[BaseModel]
    run: Callable[[httpx.AsyncClient, BaseModel], Awaitable[BaseModel]]


REGISTRY = {
    "search_candidates": Tool("선호 언어로 현재 열린 입문용 이슈 후보를 찾거나 다음 페이지에서 대안을 찾을 때 사용합니다.",
                              Search, CandidatePage, search_candidates),
    "candidate_detail": Tool("선택한 이슈의 검토 시간을 계산하기 위해 본문 길이, 댓글 수와 라벨이 필요할 때 사용합니다.",
                             IssueId, Issue, candidate_detail),
    "search_resources": Tool("선호 언어를 공부할 때 참고할 Stack Overflow 질문과 원문 출처가 필요할 때 사용합니다.",
                             Topic, Resources, search_resources),
}


def tool_specs():
    return [dict(name=name, kind="external_api", description=tool.description,
                 input_schema=tool.input.model_json_schema(),
                 output_schema=TypeAdapter(Success[tool.output] | Failure).json_schema())
            for name, tool in REGISTRY.items()]


async def invoke_tool(name, arguments, *, client=None):
    def failure(code, message):
        return {"ok": False, "error": {"code": code, "message": message}}

    if name not in REGISTRY:
        return failure("UNKNOWN_TOOL", "등록되지 않은 도구입니다.")
    tool = REGISTRY[name]
    try:
        args = tool.input.model_validate(arguments)
    except ValidationError:
        return failure("INVALID_INPUT", "도구 입력값을 확인하세요.")
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=8) as owned:
                result = await tool.run(owned, args)
        else:
            result = await tool.run(client, args)
        return {"ok": True, "data": result.model_dump(mode="json")}
    except ToolError as exc:
        return failure(exc.code, str(exc))
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            return failure("NOT_FOUND", "원본 항목이 없거나 공개되지 않았습니다.")
        if exc.response.status_code in (401, 403):
            return failure("AUTH_ERROR", "제공기관이 인증 또는 조회 권한을 거부했습니다. 서버 설정을 확인하세요.")
        return failure("UPSTREAM_ERROR", "제공기관이 요청을 처리할 수 없습니다.")
    except httpx.RequestError:
        return failure("UNAVAILABLE", "제공기관에 연결할 수 없습니다. 잠시 후 다시 시도하세요.")
    except (KeyError, TypeError, ValueError, AttributeError):
        return failure("INVALID_RESPONSE", "제공기관의 응답에서 필요한 값을 확인할 수 없습니다.")
