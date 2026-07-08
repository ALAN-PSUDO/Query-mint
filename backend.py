"""FastAPI backend for the query-mint natural-language-to-SQL engine."""

from __future__ import annotations

import os
import re
from typing import Any

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from google import generativeai as genai
from pydantic import BaseModel, Field


load_dotenv()


DB_URL = os.getenv("DB_URL", "USER:PASSWORD@HOST:5432/DB_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"

FORBIDDEN_PATTERN = re.compile(r"\b(insert|update|delete|drop|alter|truncate)\b", re.IGNORECASE)
READ_ONLY_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


SCHEMA_CONTEXT = """
Database schema:

Table: users
- user_id SERIAL PRIMARY KEY
- name VARCHAR
- email VARCHAR
- department VARCHAR
- hire_date DATE

Table: products
- product_id SERIAL PRIMARY KEY
- name VARCHAR
- category VARCHAR
- price DECIMAL
- stock_quantity INT

Table: orders
- order_id SERIAL PRIMARY KEY
- user_id INT FOREIGN KEY -> users.user_id
- product_id INT FOREIGN KEY -> products.product_id
- order_date DATE
- order_total DECIMAL

Join rules:
- orders.user_id = users.user_id
- orders.product_id = products.product_id

Rules:
- Generate only raw PostgreSQL SQL.
- Return SELECT statements only.
- Do not use markdown fences, explanations, or comments.
- Prefer readable aliases and explicit JOINs.
- If the request is vague, infer a useful analytic query from the schema.
- Use LIMIT when the request asks for top or first N rows.
""".strip()


class PromptRequest(BaseModel):
    prompt: str = Field(min_length=5)


class SqlRequest(BaseModel):
    sql: str = Field(min_length=1)


class QueryRequest(BaseModel):
    prompt: str = Field(min_length=5)
    sql: str = Field(min_length=1)


class GenerateResponse(BaseModel):
    sql: str


class QueryResponse(BaseModel):
    rows: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    message: str = ""


app = FastAPI(title="query-mint-api", version="1.0.0")


def is_blocked_text(text: str) -> bool:
    return bool(FORBIDDEN_PATTERN.search(text))


def strip_code_fences(sql_text: str) -> str:
    cleaned = sql_text.strip()
    cleaned = re.sub(r"^```(?:sql)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def is_read_only_sql(sql_text: str) -> bool:
    normalized = strip_code_fences(sql_text).strip()
    return bool(normalized) and bool(READ_ONLY_PATTERN.match(normalized)) and not is_blocked_text(normalized)


def build_prompt(user_request: str) -> str:
    return f"""
You are a PostgreSQL SQL generator for a read-only analytics app.

Follow these rules exactly:
1. Output only raw PostgreSQL SQL.
2. Use only the provided schema.
3. Return a single SELECT query.
4. Never write INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, or any other mutation.
5. If the request is ambiguous, make the most useful analytical interpretation.
6. Prefer explicit JOINs and readable aliases.
7. Include LIMIT when the request asks for top, first, or similar ranking output.

Schema:
{SCHEMA_CONTEXT}

User request:
{user_request}

SQL:
""".strip()


def configure_model() -> None:
    if "YOUR_GEMINI_API_KEY" in GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured.")
    genai.configure(api_key=GEMINI_API_KEY)


def generate_sql(user_request: str) -> str:
    if len(user_request.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please enter at least 5 characters before generating SQL.")
    if is_blocked_text(user_request):
        raise HTTPException(status_code=400, detail="Only read-only SELECT queries are allowed.")

    configure_model()
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(build_prompt(user_request))
    response_text = getattr(response, "text", "") or ""
    generated_sql = strip_code_fences(response_text)

    if not is_read_only_sql(generated_sql):
        raise HTTPException(status_code=400, detail="The generated SQL was not a read-only SELECT query.")

    return generated_sql


def run_query(sql_text: str) -> pd.DataFrame:
    if not is_read_only_sql(sql_text):
        raise HTTPException(status_code=400, detail="Only read-only SELECT queries are allowed.")

    try:
        with psycopg2.connect(DB_URL) as connection:
            with connection.cursor() as cursor:
                cursor.execute(strip_code_fences(sql_text))
                if cursor.description is None:
                    return pd.DataFrame()
                rows = cursor.fetchall()
                columns = [column.name for column in cursor.description]
                return pd.DataFrame(rows, columns=columns)
    except psycopg2.Error as exc:
        raise HTTPException(status_code=400, detail="The database could not execute that query. Please verify the SQL and connection details.") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/schema")
def schema() -> dict[str, Any]:
    return {"schema": SCHEMA_CONTEXT}


@app.post("/generate-sql", response_model=GenerateResponse)
def generate_sql_endpoint(payload: PromptRequest) -> GenerateResponse:
    return GenerateResponse(sql=generate_sql(payload.prompt))


@app.post("/execute-query", response_model=QueryResponse)
def execute_query_endpoint(payload: SqlRequest) -> QueryResponse:
    df = run_query(payload.sql)
    if df.empty:
        return QueryResponse(rows=[], columns=list(df.columns), row_count=0, message="Query ran successfully but returned no data.")

    return QueryResponse(
        rows=df.to_dict(orient="records"),
        columns=list(df.columns),
        row_count=len(df),
    )


@app.post("/query", response_model=QueryResponse)
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

