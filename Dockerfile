FROM python:3.11-slim

# libgomp1 is required by onnxruntime (chromadb transitive dep)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependencies (cached layer) ──────────────────────────────────────────────
# Railway rootDirectory=backend, so build context is backend/
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ──────────────────────────────────────────────────────────
# Copy backend/ contents into /app/backend/ so `from backend.xxx import` works
COPY . ./backend/

# ── Runtime env ───────────────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROMA_PERSIST_DIR=/app/backend/chroma_data \
    PORT=8000

EXPOSE 8000

# uvicorn is already in requirements.txt; $PORT is injected by Railway
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
