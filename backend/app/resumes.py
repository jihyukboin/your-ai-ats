import json
import logging
import sqlite3
from contextlib import closing
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from . import database
from .resume_parser import Fields, Items, Tags, extract, structure

router = APIRouter(prefix="/api/resumes")


def event(**data):
    return json.dumps(data, ensure_ascii=False) + "\n"


@router.post("")
async def upload(file: UploadFile):
    return await parse_upload(file, replace=False)


@router.put("/latest")
async def replace_latest(file: UploadFile):
    return await parse_upload(file, replace=True)


async def parse_upload(file: UploadFile, replace: bool):
    pdf = await file.read(10 * 1024 * 1024 + 1)
    await file.close()
    if len(pdf) > 10 * 1024 * 1024:
        raise HTTPException(413, "10MB 이하 PDF를 올려주세요.")
    if not pdf.startswith(b"%PDF-"):
        raise HTTPException(422, "PDF 형식을 확인해주세요.")

    async def parse():
        stage = "Upstage 문서 추출"
        try:
            async with httpx.AsyncClient(timeout=180) as client:
                yield event(step=1)
                blocks, images = await extract(client, pdf)
                yield event(step=2)
                stage = "GMS 섹션 인식"
                parsed = await structure(client, blocks, images)
            yield event(step=3)
            stage = "결과 저장"
            resume_id = str(uuid4())
            portrait = images.get(parsed.portrait_id)
            directory = database.DATABASE_PATH.parent / "avatars"
            path = directory / f"{resume_id}.jpg"
            sections = [dict(s.model_dump(), id=str(i)) for i, s in enumerate(parsed.sections)]
            result = dict(id=resume_id, name=parsed.name, sections=sections,
                          avatar=f"/api/resumes/{resume_id}/avatar" if portrait else None)
            previous = None
            try:
                if portrait:
                    directory.mkdir(exist_ok=True)
                    path.write_bytes(portrait)
                with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
                    if replace:
                        db.execute("BEGIN IMMEDIATE")
                        previous = db.execute("SELECT id FROM resumes ORDER BY rowid DESC LIMIT 1").fetchone()
                        if previous:
                            db.execute("DELETE FROM resumes WHERE id=?", previous)
                    db.execute("INSERT INTO resumes VALUES (?, ?)", (resume_id, json.dumps(result, ensure_ascii=False)))
            except Exception:
                path.unlink(missing_ok=True)
                raise
            if previous:
                try:
                    (directory / f"{previous[0]}.jpg").unlink(missing_ok=True)
                except OSError:
                    logging.getLogger(__name__).warning("Replaced avatar could not be removed")
            yield event(result=result)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            hint = {401: "서버 API 키를 확인해주세요.", 403: "키의 접근 권한을 확인해주세요.",
                    429: "사용 한도 또는 호출 빈도를 확인해주세요."}.get(status, "문서와 서비스 상태를 확인해주세요.")
            yield event(error=f"{stage} 실패 (HTTP {status}). {hint}")
        except Exception as exc:
            reason = str(exc) if type(exc) is ValueError else "파일 또는 서비스 연결을 확인해주세요."
            yield event(error=f"{stage} 실패. {reason}")
    return StreamingResponse(parse(), media_type="application/x-ndjson")


@router.get("/latest")
def latest_resume():
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        row = db.execute("SELECT document FROM resumes ORDER BY rowid DESC LIMIT 1").fetchone()
    return json.loads(row[0]) if row else None


@router.get("/{resume_id}")
def get_resume(resume_id: UUID):
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db:
        row = db.execute("SELECT document FROM resumes WHERE id=?", (str(resume_id),)).fetchone()
    if not row:
        raise HTTPException(404)
    return json.loads(row[0])


@router.put("/{resume_id}/sections/{index}")
def update_section(resume_id: UUID, index: int, section: Fields | Items | Tags):
    if index < 0:
        raise HTTPException(404)
    path = f"$.sections[{index}]"
    payload = json.dumps(dict(section.model_dump(), id=str(index)), ensure_ascii=False)
    with closing(sqlite3.connect(database.DATABASE_PATH)) as db, db:
        updated = db.execute("UPDATE resumes SET document=json_set(document, ?, json(?)) "
                             "WHERE id=? AND json_type(document, ?)='object'",
                             (path, payload, str(resume_id), path))
        if not updated.rowcount:
            raise HTTPException(404)
    return json.loads(payload)


@router.get("/{resume_id}/avatar")
def avatar(resume_id: UUID):
    path = database.DATABASE_PATH.parent / "avatars" / f"{resume_id}.jpg"
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, media_type="image/jpeg")
