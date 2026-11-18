import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .database import check_database, initialize_database


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    database: Literal["sqlite"] = "sqlite"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="AI Core Planner API", lifespan=lifespan)


@app.get("/api/health")
def health() -> HealthResponse:
    try:
        check_database()
    except sqlite3.Error as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc
    return HealthResponse()
