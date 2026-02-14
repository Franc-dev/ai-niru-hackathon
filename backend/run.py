"""
Development server runner

Can be run from project root:  python -m backend.run
Or from backend directory:     python run.py
"""
import sys
import os
import uvicorn

# Allow running from inside backend/ by adding the project root to sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from backend.main import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
