#!/bin/bash
# =============================================================================
# Lightning.ai Studio Setup Script
# Run this inside your Lightning Studio terminal
# =============================================================================

set -e

echo "========================================="
echo "  MentalChat-16K - Lightning Setup"
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
pip install -q -r deploy/lightning/requirements.txt

# 3. Verify GPU availability
echo "[3/4] Checking GPU..."
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}' if torch.cuda.is_available() else 'No GPU')"

# 4. Start the model server (MentalChat-16K downloads from HF on first run)
echo "[4/4] Starting model server on port 8002..."
echo ""
echo "========================================="
echo "  In a SECOND terminal, run localtunnel:"
echo "  npx localtunnel --port 8002 --subdomain <your-subdomain>"
echo "  Then set LOCAL_MODEL_URL=https://<your-subdomain>.loca.lt/v1/chat"
echo "========================================="
echo ""
python training/scripts/serve_local_model.py --port 8002
