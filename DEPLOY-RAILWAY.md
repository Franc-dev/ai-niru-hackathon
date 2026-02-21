# Deploy to Railway

## Checklist

1. **Root directory**: Set to **empty** (/) in Railway → Settings → Source — required so `backend` package is found

2. **Builder**: **Railpack only** — Dockerfiles renamed to `.bak` so Railway uses Railpack (no Docker)

2. **Environment variables** (required): Set in Railway → Service → Variables:
   - `MONGODB_URL` — your MongoDB connection string
   - `MONGODB_DB_NAME` — e.g. `ai_niru`.
   - `JWT_SECRET_KEY` — your secret
   - `LOCAL_MODEL_URL` — your model API URL (e.g. Lightning/localtunnel)
   - `LOCAL_EMBEDDING_URL` — same as model if using combined endpoint
   - `BACKEND_CORS_ORIGINS` — e.g. `["https://your-frontend.vercel.app"]`
   - **MONGODB_URL is required** — without it the app will crash on startup

3. **Build**: Railway auto-detects the Dockerfile. Push to trigger deploy.

4. **Health check**: `/health` — increased timeout (60s) for cold starts.
