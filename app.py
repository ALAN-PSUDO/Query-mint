"""Streamlit frontend for the query-mint FastAPI backend."""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv

from fastapi_backend.services.fallback_sql import fallback_sql_for_prompt, normalize_text


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEMO_MODE_DEFAULT = os.getenv("DEMO_MODE", "false").strip().lower() in {"1", "true", "yes", "on"}

LOCAL_SCHEMA_CONTEXT = """
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
""".strip()


def build_demo_tables() -> dict[str, pd.DataFrame]:
    today = date.today()

    users = pd.DataFrame(
        [
            (1, "Ava Carter", "ava.carter@querymint.test", "Engineering", date(2024, 2, 12)),
            (2, "Mia Brooks", "mia.brooks@querymint.test", "Sales", date(2021, 7, 19)),
            (3, "Noah Mitchell", "noah.mitchell@querymint.test", "Engineering", date(2023, 10, 3)),
            (4, "Emma Turner", "emma.turner@querymint.test", "Finance", date(2020, 5, 14)),
            (5, "Liam Morgan", "liam.morgan@querymint.test", "Product", date(2022, 11, 28)),
            (6, "Olivia Parker", "olivia.parker@querymint.test", "Engineering", date(2025, 1, 6)),
            (7, "Elijah Reed", "elijah.reed@querymint.test", "Marketing", date(2019, 9, 25)),
            (8, "Sophia Hayes", "sophia.hayes@querymint.test", "Operations", date(2023, 4, 18)),
        ],
        columns=["user_id", "name", "email", "department", "hire_date"],
    )

    products = pd.DataFrame(
        [
            (1, "Adaptive Analytics Suite", "Software", 499.00, 12),
            (2, "Core Notebook", "Office Supplies", 38.50, 0),
            (3, "Apex Workstation", "Electronics", 1250.00, 5),
            (4, "Insight Headset", "Accessories", 84.00, 0),
            (5, "Nova Monitor", "Electronics", 310.00, 18),
            (6, "Prime Keyboard", "Accessories", 64.00, 7),
        ],
        columns=["product_id", "name", "category", "price", "stock_quantity"],
    )

    orders = pd.DataFrame(
        [
            (1, 1, 3, today - timedelta(days=4), 2500.00),
            (2, 3, 1, today - timedelta(days=12), 998.00),
            (3, 6, 5, today - timedelta(days=7), 620.00),
            (4, 1, 6, today - timedelta(days=2), 128.00),
            (5, 5, 3, today - timedelta(days=17), 1250.00),
            (6, 3, 5, today - timedelta(days=29), 620.00),
            (7, 2, 2, today - timedelta(days=35), 38.50),
            (8, 4, 4, today - timedelta(days=9), 84.00),
            (9, 6, 1, today - timedelta(days=1), 499.00),
            (10, 1, 3, today - timedelta(days=21), 1250.00),
            (11, 8, 6, today - timedelta(days=5), 64.00),
            (12, 3, 3, today - timedelta(days=14), 1250.00),
        ],
        columns=["order_id", "user_id", "product_id", "order_date", "order_total"],
    )

    return {"users": users, "products": products, "orders": orders}


DEMO_TABLES = build_demo_tables()


def demo_sql_for_prompt(prompt: str) -> str:
    return fallback_sql_for_prompt(prompt) or (
        "SELECT user_id, name, email, department, hire_date FROM users ORDER BY user_id LIMIT 20;"
    )


def demo_result_for_sql(sql_text: str) -> pd.DataFrame:
    normalized = normalize_text(strip_code_fences(sql_text))
    users = DEMO_TABLES["users"]
    products = DEMO_TABLES["products"]
    orders = DEMO_TABLES["orders"]

    if "count(*) as out_of_stock_products" in normalized or ("from products" in normalized and "stock_quantity = 0" in normalized):
        return pd.DataFrame({"out_of_stock_products": [int((products["stock_quantity"] == 0).sum())]})

    if "from users" in normalized and "department = 'engineering'" in normalized and "hire_date > date '2022-12-31'" in normalized:
        result = users[(users["department"] == "Engineering") & (users["hire_date"] > date(2022, 12, 31))].copy()
        return result[["user_id", "name", "email", "department", "hire_date"]].sort_values(["hire_date", "user_id"], ascending=[False, True]).reset_index(drop=True)

    if "sum(o.order_total) as total_spend" in normalized or ("from users u" in normalized and "join orders o" in normalized and "total spend" in normalized):
        result = (
            users[["user_id", "name"]]
            .merge(orders[["user_id", "order_total"]], on="user_id", how="inner")
            .groupby(["user_id", "name"], as_index=False)["order_total"]
            .sum()
            .rename(columns={"name": "customer_name", "order_total": "total_spend"})
            .sort_values(["total_spend", "user_id"], ascending=[False, True])
            .head(5)
            .reset_index(drop=True)
        )
        return result

    if "from orders" in normalized and "current_date - interval '30 days'" in normalized:
        recent_orders = orders[orders["order_date"] >= (date.today() - timedelta(days=30))]
        result = (
            recent_orders
            .merge(users[["user_id", "name"]], on="user_id", how="left")
            .merge(products[["product_id", "name"]], on="product_id", how="left", suffixes=("_customer", "_product"))
            .rename(columns={"name_customer": "customer_name", "name_product": "product_name"})
        )
        columns = ["order_id", "customer_name", "product_name", "order_date", "order_total"]
        return result[columns].sort_values(["order_date", "order_id"], ascending=[False, False]).reset_index(drop=True)

    if "from users" in normalized:
        if "order by user_id" in normalized or "limit 20" in normalized:
            return users[["user_id", "name", "email", "department", "hire_date"]].sort_values("user_id").reset_index(drop=True)

    return pd.DataFrame()


def apply_theme() -> None:
    if st.session_state.get("_theme_applied"):
        return

    st.session_state["_theme_applied"] = True
    st.markdown(
        """
        <style>
        :root {
            --bg: #f3f7f5;
            --surface: #ffffff;
            --ink: #0f2a24;
            --muted: #5b6d66;
            --accent: #127a66;
            --accent-2: #e88a2e;
            --ring: #cde8e2;
        }

        .stApp {
            font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
            color: var(--ink);
            background:
                radial-gradient(circle at 8% 8%, #dff3ed 0%, transparent 40%),
                radial-gradient(circle at 92% 0%, #ffe7cc 0%, transparent 38%),
                var(--bg);
        }

        .main .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }

        .hero {
            background: linear-gradient(145deg, #0f2a24 0%, #154a3f 55%, #127a66 100%);
            color: #ecfffa;
            border: 1px solid #1e6152;
            border-radius: 18px;
            padding: 1.2rem 1.4rem;
            box-shadow: 0 18px 36px rgba(15, 42, 36, 0.18);
            margin-bottom: 1rem;
        }

        .hero h1 {
            margin: 0;
            font-size: 1.6rem;
            line-height: 1.25;
            letter-spacing: 0.01em;
        }

        .hero p {
            margin: 0.55rem 0 0;
            color: #d1f1e8;
        }

        .chip-row {
            margin-top: 0.8rem;
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
        }

        .chip {
            display: inline-block;
            padding: 0.24rem 0.62rem;
            border-radius: 999px;
            border: 1px solid rgba(255, 255, 255, 0.28);
            background: rgba(255, 255, 255, 0.11);
            color: #e9fffa;
            font-size: 0.78rem;
        }

        .panel-title {
            margin: 0.35rem 0 0.55rem;
            font-size: 1.03rem;
            font-weight: 700;
            color: var(--ink);
        }

        .stTextInput label, .stTextArea label {
            font-weight: 700;
            color: var(--ink) !important;
        }

        .stTextArea textarea,
        [data-testid="stTextArea"] textarea {
            font-family: Consolas, "Courier New", monospace !important;
            font-size: 0.95rem !important;
            color: #0f2a24 !important;
            background-color: #ffffff !important;
            -webkit-text-fill-color: #0f2a24 !important;
            caret-color: #0f2a24 !important;
            border: 1px solid var(--ring) !important;
        }

        .stTextInput input,
        [data-testid="stTextInput"] input {
            color: #0f2a24 !important;
            background-color: #ffffff !important;
            -webkit-text-fill-color: #0f2a24 !important;
            border: 1px solid var(--ring) !important;
        }

        .stButton > button {
            border-radius: 12px;
            border: 1px solid #cfe5df;
            background: #ffffff;
            color: var(--ink);
            font-weight: 600;
        }

        .stButton > button:hover {
            border-color: #9dcfc3;
            background: #f7fcfa;
        }

        .stDownloadButton > button {
            border-radius: 12px;
            border: 1px solid #f4c48e;
            background: #fff7ee;
            color: #8c4d0b;
            font-weight: 700;
        }

        [data-testid="stDataFrame"] {
            border: 1px solid var(--ring);
            border-radius: 12px;
            background: var(--surface);
        }

        [data-testid="stSidebar"] {
            background: #f8fcfa;
            border-right: 1px solid #dcebe6;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        f"""
        <section class="hero">
            <h1>query-mint · Ask, Inspect, Execute</h1>
            <p>Translate natural language into safe PostgreSQL, review the SQL, and run it against live data.</p>
            <div class="chip-row">
                <span class="chip">FastAPI backend</span>
                <span class="chip">Editable SQL</span>
                <span class="chip">Session history</span>
                <span class="chip">CSV export</span>
                <span class="chip">API: {API_BASE_URL}</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_quick_prompts() -> None:
    st.markdown('<div class="panel-title">Quick Start Prompts</div>', unsafe_allow_html=True)
    quick_prompts = [
        "List all users",
        "Show me all orders placed in the last 30 days",
        "How many products are out of stock?",
        "Find the top 5 customers by total spend",
        "Show all employees in the Engineering department hired after 2022",
    ]

    columns = st.columns(3)
    for index, example in enumerate(quick_prompts):
        with columns[index % len(columns)]:
            if st.button(example, key=f"quick_prompt_{index}", use_container_width=True):
                st.session_state.nl_prompt = example
                st.rerun()


def initialize_session_state() -> None:
    defaults: dict[str, Any] = {
        "nl_prompt": "",
        "sql_editor": "",
        "history": [],
        "active_history_index": None,
        "result_df": pd.DataFrame(),
        "result_count": 0,
        "last_message": "",
        "last_error": "",
        "last_query_status": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def dataframe_from_history(entry: dict[str, Any]) -> pd.DataFrame:
    rows = entry.get("rows", [])
    columns = entry.get("columns", [])
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=columns)


def set_current_result(
    prompt: str,
    sql_text: str,
    df: pd.DataFrame,
    status: str,
    message: str = "",
    error: str = "",
    *,
    update_inputs: bool = False,
) -> None:
    # Widget keys (nl_prompt / sql_editor) can only be written before those widgets render.
    if update_inputs:
        st.session_state.nl_prompt = prompt
        st.session_state.sql_editor = sql_text
    st.session_state.result_df = df
    st.session_state.result_count = len(df)
    st.session_state.last_query_status = status
    st.session_state.last_message = message
    st.session_state.last_error = error


def store_history(prompt: str, sql_text: str, df: pd.DataFrame, status: str, message: str = "", error: str = "") -> None:
    history_entry = {
        "prompt": prompt,
        "sql": sql_text,
        "status": status,
        "message": message,
        "error": error,
        "rows": df.to_dict(orient="records"),
        "columns": list(df.columns),
        "result_count": len(df),
    }
    st.session_state.history.insert(0, history_entry)
    st.session_state.history = st.session_state.history[:20]


def load_history_item(index: int) -> None:
    entry = st.session_state.history[index]
    df = dataframe_from_history(entry)
    set_current_result(
        prompt=entry.get("prompt", ""),
        sql_text=entry.get("sql", ""),
        df=df,
        status=entry.get("status", "loaded"),
        message=entry.get("message", ""),
        error=entry.get("error", ""),
        update_inputs=True,
    )
    st.session_state.active_history_index = index


def show_history_sidebar() -> None:
    st.sidebar.markdown("### Query History")
    if not st.session_state.history:
        st.sidebar.caption("No queries yet.")
        return

    for index, entry in enumerate(st.session_state.history):
        prompt_preview = entry.get("prompt", "")[:48]
        label = f"{index + 1}. {prompt_preview or 'Untitled query'}"
        if st.sidebar.button(label, key=f"history_{index}", use_container_width=True):
            load_history_item(index)


def is_blocked_text(text: str) -> bool:
    blocked_words = ("insert", "update", "delete", "drop", "alter", "truncate")
    lowered = text.lower()
    return any(word in lowered for word in blocked_words)


def is_read_only_sql(sql_text: str) -> bool:
    normalized = sql_text.strip().lower()
    return bool(normalized) and (normalized.startswith("select") or normalized.startswith("with")) and not is_blocked_text(normalized)


def strip_code_fences(sql_text: str) -> str:
    cleaned = sql_text.strip()
    cleaned = cleaned.removeprefix("```sql").removeprefix("```")
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return cleaned.strip()


def api_get(path: str, timeout: float = 5) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=timeout)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any], timeout: float = 60) -> dict[str, Any]:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()


def dataframe_from_query_payload(payload: dict[str, Any]) -> pd.DataFrame:
    rows = payload.get("rows", [])
    columns = payload.get("columns", [])
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=columns)


@st.cache_data(ttl=30, show_spinner=False)
def cached_backend_healthy(api_base: str) -> bool:
    try:
        response = requests.get(f"{api_base}/health", timeout=2)
        return response.ok
    except Exception:
        return False


@st.cache_data(ttl=120, show_spinner=False)
def cached_schema_text(api_base: str) -> str:
    try:
        response = requests.get(f"{api_base}/schema", timeout=3)
        response.raise_for_status()
        return response.json().get("schema", "")
    except Exception:
        return ""


def generate_sql_for_prompt(prompt: str, demo_mode: bool) -> str:
    if demo_mode:
        return demo_sql_for_prompt(prompt)

    local_sql = fallback_sql_for_prompt(prompt)
    if local_sql:
        return local_sql

    payload = api_post("/generate-sql", {"prompt": prompt})
    return strip_code_fences(payload.get("sql", ""))


def show_connection_status(demo_mode: bool) -> None:
    st.sidebar.markdown("### Backend Status")
    if demo_mode:
        st.sidebar.info("Demo mode is active. Queries run against local sample data.")
        return

    if cached_backend_healthy(API_BASE_URL):
        st.sidebar.success("FastAPI backend is reachable.")
    else:
        st.sidebar.error("FastAPI backend is not reachable. Turn on Demo mode or start uvicorn backend:app first.")


def parse_schema(schema_text: str) -> dict[str, list[str]]:
    schema_map: dict[str, list[str]] = {}
    current_table = ""

    for raw_line in schema_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.lower().startswith("table:"):
            current_table = line.split(":", 1)[1].strip()
            schema_map[current_table] = []
            continue

        if current_table and line.startswith("-"):
            schema_map[current_table].append(line.removeprefix("-").strip())

    return schema_map


def show_schema_sidebar(demo_mode: bool) -> None:
    st.sidebar.markdown("### Schema Explorer")
    schema_text = LOCAL_SCHEMA_CONTEXT if demo_mode else cached_schema_text(API_BASE_URL)
    if not schema_text:
        st.sidebar.caption("Schema explorer is unavailable until the backend is reachable.")
        return

    schema_map = parse_schema(schema_text)
    if not schema_map:
        st.sidebar.caption("Schema metadata is unavailable.")
        return

    for table_name, columns in schema_map.items():
        with st.sidebar.expander(table_name, expanded=False):
            for column in columns:
                st.caption(column)


def main() -> None:
    st.set_page_config(page_title="query-mint", layout="wide")
    initialize_session_state()
    apply_theme()
    render_header()

    render_quick_prompts()

    with st.sidebar:
        st.sidebar.markdown("### Mode")
        demo_mode = st.sidebar.checkbox(
            "Demo mode (no backend required)",
            value=DEMO_MODE_DEFAULT,
            help="Use local sample data and built-in SQL for testing when you do not have a database yet.",
        )
        show_connection_status(demo_mode)
        show_schema_sidebar(demo_mode)
        show_history_sidebar()

    prompt = st.text_input(
        "Ask a question about your data",
        key="nl_prompt",
        placeholder="Show the top 5 customers by total spend",
    )

    generate_col, clear_col = st.columns([1, 1])
    with generate_col:
        generate_clicked = st.button("Generate SQL", use_container_width=True)
    with clear_col:
        clear_clicked = st.button("Clear", use_container_width=True)

    if clear_clicked:
        st.session_state.nl_prompt = ""
        st.session_state.sql_editor = ""
        st.session_state.result_df = pd.DataFrame()
        st.session_state.result_count = 0
        st.session_state.last_message = ""
        st.session_state.last_error = ""
        st.session_state.last_query_status = ""
        st.session_state.active_history_index = None
        st.rerun()

    if generate_clicked:
        if len(prompt.strip()) < 5:
            st.error("Please enter at least 5 characters before generating SQL.")
        elif is_blocked_text(prompt):
            st.error("Only read-only SELECT queries are allowed.")
        else:
            try:
                with st.spinner("Generating SQL..."):
                    generated_sql = generate_sql_for_prompt(prompt, demo_mode)
                if not is_read_only_sql(generated_sql):
                    st.error("The backend generated SQL that is not read-only.")
                else:
                    st.session_state.sql_editor = generated_sql
                    st.session_state.last_message = "SQL generated successfully."
                    st.session_state.last_error = ""
                    st.session_state.last_query_status = "generated"
                    st.session_state.result_df = pd.DataFrame()
                    st.session_state.result_count = 0
                    st.session_state.active_history_index = None
            except requests.HTTPError as exc:
                detail = "Unable to generate SQL right now."
                try:
                    detail = exc.response.json().get("detail", detail)
                except Exception:
                    response_text = (exc.response.text or "").strip()
                    if response_text and response_text != "Internal Server Error":
                        detail = response_text[:240]
                st.error(detail)
            except requests.RequestException as exc:
                st.error(f"Unable to reach the backend at {API_BASE_URL}. ({type(exc).__name__})")
            except Exception as exc:
                st.error(f"SQL generation failed: {type(exc).__name__}: {exc}")

    sql_text = st.text_area(
        "Generated SQL",
        key="sql_editor",
        height=220,
        placeholder="Generated SQL will appear here and can be edited before execution.",
    )

    execute_clicked = st.button("Execute Query", type="primary")

    if execute_clicked:
        if len(prompt.strip()) < 5:
            st.error("Please enter at least 5 characters before executing a query.")
        elif not sql_text.strip():
            st.error("Generate or enter SQL before executing the query.")
        elif is_blocked_text(prompt) or is_blocked_text(sql_text):
            st.error("Only read-only SELECT queries are allowed.")
        elif not is_read_only_sql(sql_text):
            st.error("Only read-only SELECT queries are allowed.")
        else:
            try:
                with st.spinner("Running query..."):
                    if demo_mode:
                        df = demo_result_for_sql(sql_text)
                        message = ""
                    else:
                        payload = api_post("/execute-query", {"sql": sql_text})
                        df = dataframe_from_query_payload(payload)
                        message = payload.get("message", "")
                empty_message = message or "Query ran successfully but returned no data."
                if df.empty:
                    set_current_result(prompt, sql_text, df, status="success", message=empty_message)
                    store_history(prompt, sql_text, df, status="success", message=empty_message)
                else:
                    set_current_result(prompt, sql_text, df, status="success")
                    store_history(prompt, sql_text, df, status="success")
            except requests.HTTPError as exc:
                detail = "The database could not execute that query."
                try:
                    detail = exc.response.json().get("detail", detail)
                except Exception:
                    response_text = (exc.response.text or "").strip()
                    if response_text and response_text != "Internal Server Error":
                        detail = response_text[:240]
                st.error(detail)
            except requests.RequestException as exc:
                st.error(f"Unable to reach the backend at {API_BASE_URL}. ({type(exc).__name__})")
            except Exception as exc:
                if demo_mode:
                    st.error("Demo mode could not interpret that SQL. Try one of the example prompts.")
                else:
                    st.error(f"Query execution failed: {type(exc).__name__}: {exc}")

    if st.session_state.last_message and st.session_state.last_query_status == "generated":
        st.success(st.session_state.last_message)

    if st.session_state.result_count > 0 and not st.session_state.result_df.empty:
        st.markdown(f"**Showing {st.session_state.result_count} results**")
        st.dataframe(st.session_state.result_df, use_container_width=True)
        st.download_button(
            label="Download CSV",
            data=st.session_state.result_df.to_csv(index=False).encode("utf-8"),
            file_name="query-mint-results.csv",
            mime="text/csv",
        )
    elif st.session_state.last_query_status == "success" and st.session_state.result_count == 0:
        st.info("Query ran successfully but returned no data.")


if __name__ == "__main__":
    main()