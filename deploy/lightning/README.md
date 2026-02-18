# Deploy EM-NS Model Server to Lightning.ai (Free GPU)

## Why Lightning.ai?
- **Free T4 GPU** (22 GPU-hours/month on free plan)
- Persistent studio environment (your files stay)
- VS Code-like browser IDE
- Public URL for your API

## Step-by-Step Deployment

### 1. Create Account & Studio
1. Go to [lightning.ai](https://lightning.ai) and sign up (free, use GitHub login)
2. Click **"Studios"** → **"New Studio"**
3. Configure:
   - **Name:** `emns-model-server`
   - **Teamspace:** Default or personal
   - **Machine:** Select **GPU** → **T4** (free tier)
4. Click **"Start"** — it takes ~1 min to boot

### 2. Run Setup Script
Once the Studio terminal is open, run:

```bash
# Download and run the setup script
curl -sL https://raw.githubusercontent.com/Franc-dev/ai-niru-hackathon/feat/emns-training-workflow/deploy/lightning/setup.sh | bash
```

Or manually:
```bash
git clone https://github.com/Franc-dev/ai-niru-hackathon.git
cd ai-niru-hackathon
pip install torch transformers peft accelerate fastapi "uvicorn[standard]" httpx pydantic
python training/scripts/serve_model.py --port 8001
```

### 3. Expose the Port
Lightning Studios can expose ports publicly:
1. In the Studio, click the **"Ports"** tab (bottom panel)
2. Add port **8001**
3. Toggle **"Public"** to ON
4. Copy the generated **public URL** (looks like `https://xxxxxx.lightning.ai`)

### 4. Test the Endpoint
```bash
curl -X POST https://<YOUR_STUDIO_URL>/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "I feel anxious"}]}'
```

### 5. Connect Your Backend
Update your backend `.env` file:

```env
LOCAL_MODEL_URL=https://<YOUR_STUDIO_URL>/v1/chat
LOCAL_EMBEDDING_URL=https://<YOUR_STUDIO_URL>/v1/embeddings
```

Then restart your backend. Your UI will now use the GPU-powered model!

## Performance Comparison

| Setup        | Response Time | Cost   |
|-------------|--------------|--------|
| Local CPU    | 3-5 minutes  | Free   |
| Lightning T4 | 2-5 seconds  | Free (22 hrs/month) |

## Tips
- **Save GPU hours:** Stop the Studio when not in use (click "Stop")
- **Keep it running:** During demos/hackathon, leave the Studio active
- **Monitor usage:** Check your GPU hours in Settings → Billing
