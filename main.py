"""
Entry point for Docker/Railway — forwards to backend.main.
Run with: uvicorn main:app --host 0.0.0.0 --port 8000
"""
from backend.main import app

__all__ = ["app"]
