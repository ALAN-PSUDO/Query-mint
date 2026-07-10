"""SQL generation and read-only guardrails for the backend."""

from __future__ import annotations

import re

from fastapi import HTTPException
from google import generativeai as genai
from google.api_core import exceptions as google_exceptions

from fastapi_backend import config
from fastapi_backend.config import SCHEMA_CONTEXT, get_gemini_api_key
from fastapi_backend.services.fallback_sql import fallback_sql_for_prompt


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
    api_key = get_gemini_api_key()
    if not api_key or "YOUR_GEMINI_API_KEY" in api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured.")
    genai.configure(api_key=api_key)


def _generate_with_gemini(user_request: str) -> str:
    configure_model()
    model = genai.GenerativeModel(config.MODEL_NAME)
    response = model.generate_content(build_prompt(user_request))
    response_text = getattr(response, "text", "") or ""
    generated_sql = strip_code_fences(response_text)

    if not is_read_only_sql(generated_sql):
        raise HTTPException(status_code=400, detail="The generated SQL was not a read-only SELECT query.")

    return generated_sql


def generate_sql(user_request: str) -> str:
    if len(user_request.strip()) < 5:
        raise HTTPException(status_code=400, detail="Please enter at least 5 characters before generating SQL.")
    if is_blocked_text(user_request):
        raise HTTPException(status_code=400, detail="Only read-only SELECT queries are allowed.")

    try:
        return _generate_with_gemini(user_request)
    except HTTPException:
        raise
    except google_exceptions.ResourceExhausted as exc:
        fallback_sql = fallback_sql_for_prompt(user_request)
        if fallback_sql and is_read_only_sql(fallback_sql):
            return fallback_sql
        raise HTTPException(
            status_code=503,
            detail="Gemini API quota exceeded. Check billing/limits at https://ai.dev/rate-limit or try again in a minute.",
        ) from exc
    except google_exceptions.GoogleAPIError as exc:
        fallback_sql = fallback_sql_for_prompt(user_request)
        if fallback_sql and is_read_only_sql(fallback_sql):
            return fallback_sql
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {str(exc)[:240]}",
        ) from exc
    except Exception as exc:
        fallback_sql = fallback_sql_for_prompt(user_request)
        if fallback_sql and is_read_only_sql(fallback_sql):
            return fallback_sql
        raise HTTPException(
            status_code=502,
            detail="Unable to generate SQL from the language model right now.",
        ) from exc
