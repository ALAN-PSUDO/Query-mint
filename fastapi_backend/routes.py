"""API route handlers for the query-mint backend."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from fastapi_backend.config import SCHEMA_CONTEXT
from fastapi_backend.schemas import GenerateResponse, PromptRequest, QueryRequest, QueryResponse, SqlRequest
from fastapi_backend.services.query_service import run_query
from fastapi_backend.services.sql_service import generate_sql


router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/schema")
def schema() -> dict[str, Any]:
    return {"schema": SCHEMA_CONTEXT}


@router.post("/generate-sql", response_model=GenerateResponse)
def generate_sql_endpoint(payload: PromptRequest) -> GenerateResponse:
    return GenerateResponse(sql=generate_sql(payload.prompt))


@router.post("/execute-query", response_model=QueryResponse)
def execute_query_endpoint(payload: SqlRequest) -> QueryResponse:
    df = run_query(payload.sql)
    if df.empty:
        return QueryResponse(rows=[], columns=list(df.columns), row_count=0, message="Query ran successfully but returned no data.")

    return QueryResponse(
        rows=df.to_dict(orient="records"),
        columns=list(df.columns),
        row_count=len(df),
    )


@router.post("/query", response_model=QueryResponse)
def query_endpoint(payload: QueryRequest) -> QueryResponse:
    generated_sql = generate_sql(payload.prompt)
    df = run_query(generated_sql)
    if df.empty:
        return QueryResponse(rows=[], columns=list(df.columns), row_count=0, message="Query ran successfully but returned no data.")

    return QueryResponse(
        rows=df.to_dict(orient="records"),
        columns=list(df.columns),
        row_count=len(df),
    )
