"""Streamlit frontend for the query-mint FastAPI backend."""

from __future__ import annotations

import os
from typing import Any

import pandas as pd
import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

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
            font-family: 'Space Grotesk', sans-serif;
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
            color: var(--ink);
        }

        .stTextArea textarea {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            border: 1px solid var(--ring);
        }

        .stTextInput input {
            border: 1px solid var(--ring);
        }

        .stButton > button {
            border-radius: 12px;
            border: 1px solid #cfe5df;
            background: #ffffff;
            color: var(--ink);
            font-weight: 600;
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            border-color: #9dcfc3;
            background: #f7fcfa;
            transform: translateY(-1px);
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
    ]

    columns = st.columns(4)
    for index, example in enumerate(quick_prompts):
        with columns[index]:
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


def set_current_result(prompt: str, sql_text: str, df: pd.DataFrame, status: str, message: str = "", error: str = "") -> None:
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


def api_get(path: str) -> dict[str, Any]:
    response = requests.get(f"{API_BASE_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def show_connection_status() -> None:
    st.sidebar.markdown("### Backend Status")
    try:
        api_get("/health")
        st.sidebar.success("FastAPI backend is reachable.")
    except Exception:
        st.sidebar.error("FastAPI backend is not reachable. Start uvicorn backend:app first.")


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


def show_schema_sidebar() -> None:
    st.sidebar.markdown("### Schema Explorer")
    try:
        payload = api_get("/schema")
        schema_text = payload.get("schema", "")
        schema_map = parse_schema(schema_text)

        if not schema_map:
            st.sidebar.caption("Schema metadata is unavailable.")
            return

        for table_name, columns in schema_map.items():
            with st.sidebar.expander(table_name, expanded=False):
                for column in columns:
                    st.caption(column)
    except Exception:
        st.sidebar.caption("Schema explorer is unavailable until the backend is reachable.")


def main() -> None:
    st.set_page_config(page_title="query-mint", layout="wide")
    initialize_session_state()
    apply_theme()
    render_header()

    render_quick_prompts()

    with st.sidebar:
        show_connection_status()
        show_schema_sidebar()
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
                payload = api_post("/generate-sql", {"prompt": prompt})
                generated_sql = strip_code_fences(payload.get("sql", ""))
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
                    pass
                st.error(detail)
            except Exception:
                st.error("Unable to reach the backend right now.")

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
                payload = api_post("/execute-query", {"sql": sql_text})
                df = pd.DataFrame(payload.get("rows", []), columns=payload.get("columns", []))
                message = payload.get("message", "")
                if df.empty:
                    set_current_result(prompt, sql_text, df, status="success", message=message or "Query ran successfully but returned no data.")
                    store_history(prompt, sql_text, df, status="success", message=message or "Query ran successfully but returned no data.")
                else:
                    set_current_result(prompt, sql_text, df, status="success")
                    store_history(prompt, sql_text, df, status="success")
            except requests.HTTPError as exc:
                detail = "The database could not execute that query."
                try:
                    detail = exc.response.json().get("detail", detail)
                except Exception:
                    pass
                st.error(detail)
            except Exception:
                st.error("Unable to reach the backend right now.")

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