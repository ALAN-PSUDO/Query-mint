# Query-mint

Query-mint is a two-process natural-language-to-SQL app with a FastAPI backend and a Streamlit frontend. A user can type a plain-English data request, inspect the generated SQL, edit it if needed, run it against PostgreSQL, and view the results in a table with history and CSV export.

## What it uses

- Python
- Streamlit for the UI
- FastAPI for the backend API
- PostgreSQL for the database
- psycopg2-binary for database access
- Google Generative AI for SQL generation
- pandas for result handling

## Database schema

The seeded database contains three related tables:

- `users`: `user_id`, `name`, `email`, `department`, `hire_date`
- `products`: `product_id`, `name`, `category`, `price`, `stock_quantity`
- `orders`: `order_id`, `user_id`, `product_id`, `order_date`, `order_total`

The schema supports common analytic queries such as user lookup, stock checks, and order/spend aggregations. `orders.user_id` references `users.user_id`, and `orders.product_id` references `products.product_id`.

## Local setup

1. Create and activate the project virtual environment if needed.
2. Install dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Set your environment variables in the terminal:

```powershell
$env:DB_URL = "postgresql://USER:PASSWORD@HOST:5432/DB_NAME?sslmode=require"
$env:GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
$env:API_BASE_URL = "http://127.0.0.1:8000"
```

Or create a `.env` file in the project root using the same keys.

4. Start the FastAPI backend:

```powershell
.\.venv\Scripts\uvicorn.exe backend:app --reload
```

5. Seed the database:

```powershell
.\.venv\Scripts\python.exe seed.py
```

6. Launch the Streamlit frontend:

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

## Features implemented

- Natural-language input for SQL generation
- Generated SQL display before execution
- Editable SQL text area
- Query execution against PostgreSQL
- Dynamic results table with row count
- Query history in the sidebar
- Zero-row handling
- Read-only query enforcement
- CSV export of the current result set

## Assumptions and trade-offs

- The app now uses a FastAPI backend for SQL generation and query execution, with Streamlit serving as the interface.
- SQL generation is constrained to read-only analytics queries for safety.
- The schema is compact and opinionated so the model has enough context to produce reliable SQL quickly.
- The project expects a valid PostgreSQL connection string and Gemini API key to be provided through environment variables.

## Query speed and caching

To speed up repeated or similar queries, I would cache generated SQL by normalized prompt and cache query results by SQL text plus a schema/version hash. That would reduce repeated Gemini calls and database hits for identical requests. The trade-off is staleness: cached results can become outdated after data changes, so the cache needs a clear invalidation policy or TTL.