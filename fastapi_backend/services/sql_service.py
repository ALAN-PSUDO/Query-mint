"""SQL generation and read-only guardrails for the backend."""

from __future__ import annotations

import re

from fastapi import HTTPException
from google import generativeai as genai

from fastapi_backend.config import GEMINI_API_KEY, MODEL_NAME, SCHEMA_CONTEXT


FORBIDDEN_PATTERN = re.compile(r"\b(insert|update|delete|drop|alter|truncate)\b", re.IGNORECASE)
READ_ONLY_PATTERN = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)


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
