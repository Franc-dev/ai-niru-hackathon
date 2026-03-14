---
title: MentalChat-16K
emoji: 🧠
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: false
license: mit
preload_from_hub:
  - khazarai/MentalChat-16K
---

# MentalChat-16K – ZeroGPU

Mental health support model (Llama 3.2 1B) on Hugging Face ZeroGPU.

## API for ai-niru backend

Set your backend `.env`:

```
LOCAL_MODEL_URL=https://<YOUR_USERNAME>-mentalchat-16k.hf.space
```

Replace `<YOUR_USERNAME>` with your Hugging Face username. The backend auto-detects Gradio Spaces and calls `/api/predict`.

## Deploy

1. **Create a new Space** at [hf.co/spaces](https://huggingface.co/spaces)
2. **SDK:** Gradio
3. **Hardware:** ZeroGPU (Settings → Hardware → ZeroGPU; **requires PRO** to host)
4. **Copy** `app.py`, `requirements.txt`, and this README into the Space

Or clone and push:

```bash
# Create Space first at hf.co/spaces, then:
git clone https://huggingface.co/spaces/<YOUR_USERNAME>/mentalchat-16k
cd mentalchat-16k
cp /path/to/ai-niru-hackathon/deploy/zerogpu/* .
git add .
git commit -m "Add MentalChat-16K ZeroGPU"
git push
```

## Usage

- **Free users:** Can use existing ZeroGPU Spaces (3.5 min/day quota)
- **PRO users:** Can host ZeroGPU Spaces; 25 min/day when using
