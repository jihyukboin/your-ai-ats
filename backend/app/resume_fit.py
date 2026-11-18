import asyncio
import json
import sqlite3
from contextlib import closing
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, StringConstraints

from . import database
from .company_analysis import now
from .fit_evidence import Matches, Requirements, compare, generate, resume_evidence, sources, verified_requirements

router = APIRouter(prefix="/api/companies/{company_id}/fit-analyses", tags=["이력서 적합도"])


class FitRequest(BaseModel):
    analysis_id: UUID
    role: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


def persist(company_id, run):
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
        db.execute("INSERT INTO resume_fits VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data",
                   (run["id"], company_id, json.dumps(run, ensure_ascii=False)))


def load_inputs(company_id, body):
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        db.execute("BEGIN")
        company = db.execute("SELECT name FROM companies WHERE id=?", (company_id,)).fetchone()
        if not company:
            raise HTTPException(404, "기업을 찾을 수 없습니다.")
        row = db.execute("SELECT data FROM company_analyses WHERE company_id=? AND id=?",
                         (company_id, str(body.analysis_id))).fetchone()
        if not row:
            raise HTTPException(404, "해당 기업의 1단계 분석을 찾을 수 없습니다.")
        analysis = json.loads(row[0])
        if analysis["status"] not in ("done", "partial") or body.role.casefold() != analysis["role"].strip().casefold():
            raise HTTPException(409, "같은 직무의 1단계 분석을 먼저 완료해주세요.")
        row = db.execute("SELECT document FROM resumes ORDER BY rowid DESC LIMIT 1").fetchone()
        if not row:
            raise HTTPException(409, "이력서를 먼저 등록해주세요.")
        return company[0], analysis, json.loads(row[0])


@router.post("", response_class=StreamingResponse, responses={200: {"content": {"application/x-ndjson": {}}}})
async def evaluate(company_id: int, body: FitRequest):
    company, analysis, resume = load_inputs(company_id, body)
    entries = sources(analysis)
    sections = resume_evidence(resume)
    run = dict(id=str(uuid4()), company_id=company_id, analysis_id=str(body.analysis_id), resume_id=resume["id"],
               role=body.role, started=now(), status="running", stages=[], result=None)

    def snapshot():
        persist(company_id, run)
        return json.dumps(run, ensure_ascii=False) + "\n"

    def stage(label):
        if run["stages"]:
            run["stages"][-1].update(status="done", ended=now())
        run["stages"].append(dict(label=label, status="running", started=now()))
        return snapshot()

    async def stream():
        try:
            yield stage("요구사항 확인")
            extracted = await generate(Requirements,
                "해당 직무의 요건만 중복 없이 추출한다. source_index는 자료 배열의 0부터 시작하는 번호이며 quote는 "
                "원문 그대로 인용한다. official=true이고 해당 기업의 특정 채용 공고에 필수 또는 우대로 명시된 경우만 "
                "required 또는 preferred, 나머지는 general. 기업 소개·사업 목표 등은 제외한다. 자료에서 요건을 "
                "충분히 찾기 어려우면 해당 직무에서 일반적으로 요구되는 역량을 general로 보충해 최소 5개를 제시하고, "
                "이때 source_index는 -1, quote는 빈 문자열로 둔다.",
                dict(company=company, role=body.role, sources=entries))
            requirements = verified_requirements(extracted.items, entries)
            yield stage("이력서 근거 찾기")
            assessed = await generate(Matches,
                "각 요구사항을 인덱스 순으로 빠짐없이 평가한다. 직접 일치 direct, 유사 경험 related, "
                "미기재 unconfirmed. 실무 경험과 자격증을 구분한다. 확인 시 해당 섹션 ID와 단일 값의 정확한 "
                "원문 구절을 인용한다. 미확인 시 두 문자열은 비운다. reason은 근거와 판단 이유, suggestion은 "
                "부족한 증거를 보완할 구체적인 제안이다. 모든 항목의 reason과 suggestion을 반드시 채운다. "
                "미기재를 지원자의 능력 부재로 단정하지 않는다.",
                dict(role=body.role, requirements=requirements, sections=sections))
            yield stage("근거 검증")
            result = compare(requirements, assessed.items, sections)
            yield stage("결과 정리")
            run.update(result=result, status="done")
        except (asyncio.CancelledError, GeneratorExit):
            run.update(status="interrupted", ended=now())
            run["stages"][-1].update(status="interrupted", ended=run["ended"])
            persist(company_id, run)
            raise
        except Exception as exc:
            run["status"] = "failed"
            run["error"] = (f"GMS HTTP {exc.response.status_code}" if isinstance(exc, httpx.HTTPStatusError)
                            else str(exc) if type(exc) is ValueError else "평가 처리 또는 GMS 응답 오류")
        run["ended"] = now()
        run["stages"][-1].update(status=run["status"], ended=run["ended"])
        yield snapshot()
    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.get("")
def history(company_id: int):
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        rows = db.execute("SELECT data FROM resume_fits WHERE company_id=? ORDER BY rowid DESC", (company_id,))
        return [json.loads(r[0]) for r in rows]


@router.get("/{fit_id}")
def detail(company_id: int, fit_id: UUID):
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        row = db.execute("SELECT data FROM resume_fits WHERE id=? AND company_id=?", (str(fit_id), company_id)).fetchone()
    if not row:
        raise HTTPException(404, "평가 기록을 찾을 수 없습니다.")
    return json.loads(row[0])
