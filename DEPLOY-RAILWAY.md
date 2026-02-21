# Deploy to Railway

## Checklist

1. **Root directory**: In Railway → Service → Settings → **Root Directory** must be **empty** (or `/`). Do NOT set it to `backend` — the Dockerfile expects the full repo.

2. **Environment variables**: Set in Railway → Service → Variables:
   - `MONGODB_URL` — your MongoDB connection string
   - `MONGODB_DB_NAME` — e.g. `ai_niru`
   - `JWT_SECRET_KEY` — your secret
   - `LOCAL_MODEL_URL` — your model API URL (e.g. Lightning/localtunnel)
   - `LOCAL_EMBEDDING_URL` — same as model if using combined endpoint
   - `BACKEND_CORS_ORIGINS` — e.g. `["https://your-frontend.vercel.app"]`

3. **Build**: Railway auto-detects the Dockerfile. Push to trigger deploy.

4. **Health check**: `/health` endpoint is used by Railway.
