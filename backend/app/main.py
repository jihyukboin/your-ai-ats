import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .companies import router as companies_router
from .company_analysis import router as analysis_router
from .cover_letter import router as letter_router
from .resumes import router as resumes_router
from .resume_fit import router as fit_router
from .database import check_database, initialize_database


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    database: Literal["sqlite"] = "sqlite"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="AI Core Planner API", lifespan=lifespan)
app.include_router(companies_router)
app.include_router(analysis_router)
app.include_router(fit_router)
app.include_router(letter_router)
app.include_router(resumes_router)


@app.get("/api/health")
def health() -> HealthResponse:
    try:
        check_database()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return HealthResponse()
