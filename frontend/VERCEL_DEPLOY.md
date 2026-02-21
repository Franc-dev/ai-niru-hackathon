# Deploy Frontend to Vercel

## 1. Connect repo to Vercel

- Go to [vercel.com](https://vercel.com) → New Project → Import your repo
- **Root Directory**: `frontend`
- **Framework Preset**: Vite

## 2. Environment variable (optional)

`.env.production` already sets the Railway API URL. If you override:

- **Key**: `VITE_API_BASE_URL`
- **Value**: `https://ai-niru-hackathon-production.up.railway.app/api/v1`

## 3. Add CORS in Railway

In Railway → Variables, add your Vercel URL to `BACKEND_CORS_ORIGINS` (comma-separated):

```
http://localhost:3000,http://localhost:5173,https://YOUR-APP.vercel.app
```

Replace `YOUR-APP` with your Vercel project name (e.g. `ai-niru-hackathon`).

## 4. Deploy

Click Deploy. The frontend will use the Railway backend.
