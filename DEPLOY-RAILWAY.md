# Deploy to Railway

## Checklist

1. **Root directory**: Set to **empty** (/) — required for Railpack so `backend` package is found

2. **Builder**: Uses **Railpack** (not Docker) — see `railway.toml`. If Railway still picks Docker, rename `Dockerfile` and `backend/Dockerfile` to `Dockerfile.bak` temporarily

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
