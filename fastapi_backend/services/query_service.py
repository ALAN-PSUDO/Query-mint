"""Database query execution for read-only SQL requests."""

from __future__ import annotations

import pandas as pd
import psycopg2
from fastapi import HTTPException

from fastapi_backend.config import DB_URL
from fastapi_backend.services.sql_service import is_read_only_sql, strip_code_fences


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
