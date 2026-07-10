"""Configuration and static schema context for the FastAPI backend."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)

DB_URL = (
    os.getenv("DB_URL")
    or os.getenv("DATABASE_URL")
    or os.getenv("NEON_DATABASE_URL")
    or "USER:PASSWORD@HOST:5432/DB_NAME"
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


def get_gemini_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    return os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")

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
