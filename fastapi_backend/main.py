"""FastAPI application assembly for query-mint."""

from __future__ import annotations

from fastapi import FastAPI

from fastapi_backend.routes import router


app = FastAPI(title="query-mint-api", version="1.0.0")
app.include_router(router)
