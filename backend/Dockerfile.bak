# For Railway when Root Directory = backend
# Build context is backend/ so we copy into /app/backend/ to preserve package structure
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend contents into /app/backend/ so "backend" package is importable
COPY . ./backend/

EXPOSE 8000
# Read PORT from env at runtime (Railway injects it)
CMD ["python", "-c", "import os; import uvicorn; from backend.main import app; uvicorn.run(app, host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))"]
