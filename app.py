"""Vercel/FastAPI entrypoint. Run: uvicorn app:app --reload."""
from pathlib import Path

from fastapi.staticfiles import StaticFiles

from demo.api import app

DIST = Path(__file__).parent / "frontend-dist"
if DIST.is_dir():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")

