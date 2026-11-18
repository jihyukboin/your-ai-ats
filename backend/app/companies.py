import sqlite3
from contextlib import closing

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from . import database

router = APIRouter(prefix="/api/companies")


class CompanyName(BaseModel):
    name: str = Field(max_length=60, min_length=1)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value):
        return " ".join(value.split()) if isinstance(value, str) else value


def query(sql, parameters=()):
    with closing(sqlite3.connect(database.DATABASE_PATH)) as connection, connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(sql, parameters)]


@router.get("")
def list_companies():
    return query("SELECT id, name FROM companies ORDER BY id DESC")


@router.post("", status_code=201)
def create_company(company: CompanyName):
    return query("INSERT INTO companies(name) VALUES (?) RETURNING id, name", (company.name,))[0]


@router.put("/{company_id}")
def update_company(company_id: int, company: CompanyName):
    rows = query("UPDATE companies SET name=? WHERE id=? RETURNING id, name", (company.name, company_id))
    if not rows:
        raise HTTPException(404, "기업을 찾을 수 없습니다.")
    return rows[0]


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int):
    if not query("DELETE FROM companies WHERE id=? RETURNING id", (company_id,)):
        raise HTTPException(404, "기업을 찾을 수 없습니다.")
