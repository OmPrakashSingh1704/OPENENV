"""
Server entry point for openenv validate / multi-mode deployment.
Delegates to the top-level app.py.
"""
import uvicorn
from app import app  # noqa: F401 — re-exported for openenv


def start():
    uvicorn.run("app:app", host="0.0.0.0", port=7860)
