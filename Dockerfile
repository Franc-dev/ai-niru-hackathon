# ── Elevana Backend ──────────────────────────────────────────────────────────
# Build context: repo root  (so `from backend.xxx import ...` resolves)
# Railway injects $PORT at runtime; defaults to 8000.

FROM python:3.11-slim

# libgomp1 — required by onnxruntime, which chromadb pulls in transitively
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencies (cached layer) ───────────────────────────────────────────────
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
COPY backend/ ./backend/

# ── Runtime config ────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # chromadb persists inside the copied backend dir
    CHROMA_PERSIST_DIR=/app/backend/chroma_data \
    PORT=8000

# Expose for documentation; Railway uses $PORT, not this
EXPOSE 8000

# Railway overrides $PORT — sh -c lets the shell expand the variable
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
