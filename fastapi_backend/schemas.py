"""Pydantic request and response models for backend endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


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
