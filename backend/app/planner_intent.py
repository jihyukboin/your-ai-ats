"""Interpret the user's portfolio reading request without inventing schedule constraints."""
import json
import os
import re
from datetime import date, timedelta

import httpx

from .planner_tools import tool_specs

LANGUAGES = {
    "Python": ["python", "파이썬"], "JavaScript": ["javascript", "자바스크립트"],
    "TypeScript": ["typescript", "타입스크립트"], "Java": ["java", "자바"],
    "Rust": ["rust", "러스트"], "Go": ["go", "golang", "고랭"], "Kotlin": ["kotlin", "코틀린"],
    "Swift": ["swift", "스위프트"], "Ruby": ["ruby", "루비"], "C++": ["c++", "씨플러스플러스"],
    "C#": ["c#", "씨샵"], "C": ["c", "씨언어"], "PHP": ["php"], "Dart": ["dart", "다트"],
    "Scala": ["scala", "스칼라"], "R": ["r"], "Shell": ["shell", "셸"],
}
TIME = re.compile(r"(?<!\d)(오전|오후|아침|저녁|밤|낮)?\s*(\d{1,2})(?::(\d{2})|\s*시(?!간)(?:\s*(\d{1,2})\s*분|\s*(반))?)")
HELP = re.compile(r"^(안녕(?:하세요)?|반가워요?|도움말|사용법|사용 방법|hello|help)[.!?\s]*$", re.I)
RESOURCES = re.compile(r"참고|자료|질문|stackoverflow|스택\s*오버플로", re.I)


def clock(minutes):
    return f"{minutes // 60:02}:{minutes % 60:02}"


def minutes(value):
    h, m = map(int, value.split(":"))
    return 60 * h + m


def extract(message, today):
    """Return only fields explicitly mentioned; an invalid date/time needs clarification."""
    changes = {}
    for language, aliases in LANGUAGES.items():
        if any(re.search(r"(?<![a-zA-Z])" + re.escape(alias) + r"(?![a-zA-Z])", message, re.I)
               for alias in aliases):
            changes["language"] = language
            break
    if "language" not in changes:
        tag = re.search(r"(?<![A-Za-z0-9])([A-Za-z][A-Za-z0-9+.#-]{0,31})\s*(?:언어|이슈|자료)", message)
        tag = tag or re.search(r"언어(?:는|를|로|를)?\s*([A-Za-z][A-Za-z0-9+.#-]{0,31})", message)
        tag = tag or re.fullmatch(r"\s*([A-Za-z][A-Za-z0-9+.#-]{0,31})\s*", message)
        if tag and tag[1].casefold() not in {"help", "hello"}:
            changes["language"] = tag[1]
    if match := re.search(r"(?<!\d)(\d{4})[-./년]\s*(\d{1,2})[-./월]\s*(\d{1,2})(?!\d)", message):
        changes["date"] = date(*map(int, match.groups())).isoformat()
    elif match := re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", message):
        changes["date"] = date(today.year, *map(int, match.groups())).isoformat()
    elif match := re.search("모레|내일|오늘", message):
        changes["date"] = (today + timedelta(days={"오늘": 0, "내일": 1, "모레": 2}[match[0]])).isoformat()
    elif match := re.search(r"(이번\s*주|다음\s*주)?\s*([월화수목금토일])요일", message):
        day = "월화수목금토일".index(match[2])
        offset = day - today.weekday()
        if match[1] and "다음" in match[1]:
            offset += 7
        elif not match[1]:
            offset %= 7
        changes["date"] = (today + timedelta(days=offset)).isoformat()

    times = list(TIME.finditer(message))
    preceding_period = None
    for idx, match in enumerate(times):
        period, h, m, m2, half = match.groups()
        hour, minute = int(h), int(m or m2 or (30 if half else 0))
        if not period and idx and match[3] is None and hour < 12:
            period = preceding_period
        preceding_period = period
        if (period and not 1 <= hour <= 12) or hour >= 24 or minute >= 60:
            raise ValueError("시각은 00:00부터 23:59까지 입력할 수 있어요.")
        if period:
            hour = hour % 12 + (12 if period in {"오후", "저녁", "밤", "낮"} else 0)
        following = message[match.end():].lstrip()
        preceding = message[max(0, match.start()-18):match.start()]
        end = bool(re.match(r"(까지|이전|전에|전\b)", following) or re.search(r"(마감|종료|끝)\s*(시각|시간)?\s*(?:만|은|는|을|를|은요)?\s*$", preceding))
        field = "end_time" if end or idx > 0 else "start_time"
        changes[field] = clock(60 * hour + minute)
    if len(times) > 2:
        raise ValueError("검토할 시간 구간 하나의 시작과 종료 시각을 알려 주세요.")
    # Only match explicit durations, not the minute component of a clock such as "2시 30분".
    duration_text = TIME.sub(" ", message)
    duration = re.search(r"(?:(\d+)\s*시간(?:\s*(\d+)\s*분)?|(\d+)\s*분)\s*(?:동안|이내|만|안에|쓸|쯤)", duration_text)
    if duration:
        changes["duration"] = 60 * int(duration[1] or 0) + int(duration[2] or duration[3] or 0)
    return changes


def rule_intent(message, changes, previous):
    if HELP.fullmatch(message.strip()) or ("사용법" in message and not changes):
        return "help", "인사 또는 사용 방법을 묻는 요청입니다."
    if RESOURCES.search(message) and not re.search(r"계획|이슈|부터|까지|기여", message):
        return "resources", "해당 언어의 참고 자료를 조회하는 요청입니다."
    if (changes and (set(changes) != {"language"} or previous or message.strip().casefold() in
                     {a.casefold() for aliases in LANGUAGES.values() for a in aliases})) or re.search("계획|이슈|기여|같은 조건|다른 후보|다른 걸", message):
        return "plan", "이슈 검토 계획 또는 일정 조건 변경을 요청했습니다."
    return None, ""


async def model_intent(message, previous):
    """A free-form request can select a registered entry tool via function calling.

    The planner consumes selection_reason before validating and dispatching tool arguments.
    An issue-detail lookup is a dependent step; the model cannot synthesize an issue ID.
    """
    gms = os.getenv("GMS_API_KEY")
    key = gms or os.getenv("OPENAI_API_KEY")
    if not key:
        return None, None, "모델 API 키가 없어 자유 형식 요청을 분류할 수 없습니다. 서버에 GMS_API_KEY 또는 OPENAI_API_KEY를 설정하거나, 언어·날짜·시작과 종료 시각을 직접 입력해 주세요."
    endpoint = ("https://gms.ssafy.io/gmsapi/api.openai.com/v1" if gms else "https://api.openai.com/v1")
    offered = []
    for spec in tool_specs():
        if spec["name"] == "candidate_detail":
            continue
        language_schema = spec["input_schema"]["properties"]["language"]
        offered.append(dict(type="function", name=spec["name"], description=spec["description"],
                            parameters=dict(type="object", properties={
                                "language": language_schema,
                                "selection_reason": {"type": "string", "description": "선택 근거 한 문장"},
                            }, required=["language", "selection_reason"], additionalProperties=False)))
    body = dict(
        model=os.getenv("PLANNER_MODEL", "gpt-4.1"), store=False, tools=offered, parallel_tool_calls=False,
        instructions="개발 포트폴리오용 검토 일정과 언어 학습 참고자료를 구분한다. 적절한 도구 하나를 선택한다. "
        "language는 요청이나 이전 조건에서 확인한 GitHub 언어명이다. 언어 또는 의도가 불명확하거나 지원하지 않는 요청이면 "
        "도구 호출 없이 사용자에게 되묻는다. selection_reason에는 선택한 기능의 공개용 근거를 한 문장으로 요약한다.",
        input=json.dumps({"request": message, "previous_conditions": previous}, ensure_ascii=False),
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(endpoint + "/responses", headers={"Authorization": "Bearer " + key}, json=body)
            response.raise_for_status()
        for output in response.json()["output"]:
            if output["type"] == "function_call" and output["name"] in {"search_candidates", "search_resources"}:
                args = json.loads(output["arguments"])
                language, reason = args["language"], args["selection_reason"]
                if re.fullmatch(r"[A-Za-z][A-Za-z0-9+#.\-]{0,31}", language) and isinstance(reason, str) and reason.strip():
                    return output["name"], language, reason[:220]
        return None, None, "모델이 요청에서 필요한 도구나 언어를 결정하지 못했습니다."
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None, None, "모델 응답을 확인할 수 없습니다. 언어와 검토 시간을 직접 입력해 주세요."
