# Deploy MentalChat-16K to Lightning.ai (Free GPU)

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
   - **Name:** `mentalchat-16k`
   - **Teamspace:** Default or personal
   - **Machine:** Select **GPU** → **T4** (free tier)
4. Click **"Start"** — it takes ~1 min to boot

### 2. Run Setup Script
Once the Studio terminal is open, run:

```bash
curl -sL https://raw.githubusercontent.com/Franc-dev/ai-niru-hackathon/main/deploy/lightning/setup.sh | bash
```

Or manually:
```bash
git clone https://github.com/Franc-dev/ai-niru-hackathon.git
cd ai-niru-hackathon
pip install -r deploy/lightning/requirements.txt
python training/scripts/serve_local_model.py --port 8002
```

*(MentalChat-16K downloads from Hugging Face on first run.)*

### 3. Expose with Localtunnel
Lightning's built-in port exposure may not work for API calls. Use **localtunnel** instead:

1. **First terminal:** Model server (from step 2) running on port 8002
2. **Second terminal** in the same Studio:
   ```bash
   npx localtunnel --port 8002 --subdomain whole-dryers-drum
   ```
   *(Pick any available subdomain; `whole-dryers-drum` is an example.)*

3. You'll get a URL like `https://whole-dryers-drum.loca.lt`

### 4. Test the Endpoint
```bash
curl -X POST https://whole-dryers-drum.loca.lt/v1/chat \
  -H "Content-Type: application/json" \
  -H "Bypass-Tunnel-Reminder: true" \
  -d '{"messages": [{"role": "user", "content": "I feel anxious"}]}'
```

*(The `Bypass-Tunnel-Reminder` header skips localtunnel's "Click to continue" page.)*

### 5. Connect Your Backend
Update your backend `.env`:

```env
LOCAL_MODEL_URL=https://whole-dryers-drum.loca.lt/v1/chat
LOCAL_EMBEDDING_URL=https://whole-dryers-drum.loca.lt/v1/embeddings
```

Then restart your backend. The agent already sends `Bypass-Tunnel-Reminder` for localtunnel.

## Performance

| Setup        | Response Time | Cost   |
|-------------|--------------|--------|
| Local CPU   | 30–60+ sec   | Free   |
| Lightning T4| 2–5 sec      | Free (22 hrs/month) |

## Tips
- **Save GPU hours:** Stop the Studio when not in use
- **Monitor usage:** Settings → Billing
