#!/bin/bash
# =============================================================================
# Lightning.ai Studio Setup Script
# Run this inside your Lightning Studio terminal
# =============================================================================

set -e

echo "========================================="
echo "  EM-NS Model Server - Lightning Setup"
echo "========================================="

# 1. Clone your repo (if not already cloned)
if [ ! -d "ai-niru-hackathon" ]; then
    echo "[1/4] Cloning repository..."
    git clone https://github.com/Franc-dev/ai-niru-hackathon.git
else
    echo "[1/4] Repository already exists, pulling latest..."
    cd ai-niru-hackathon && git pull && cd ..
fi

cd ai-niru-hackathon

# 2. Install Python dependencies
echo "[2/4] Installing dependencies..."
pip install -q torch transformers peft accelerate fastapi "uvicorn[standard]" httpx pydantic

# 3. Verify GPU availability
echo "[3/4] Checking GPU..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}' if torch.cuda.is_available() else 'No GPU')"

# 4. Start the model server
echo "[4/4] Starting model server on port 8001..."
echo ""
echo "========================================="
echo "  Server will be available at:"
echo "  https://<your-studio-name>.lightning.ai/api/v1/chat"
echo "========================================="
echo ""
python training/scripts/serve_model.py \
    --base-model Qwen/Qwen2.5-1.5B-Instruct \
    --adapter-path training/artifacts/emns-chat-lora-v1 \
    --port 8001 \
    --host 0.0.0.0
