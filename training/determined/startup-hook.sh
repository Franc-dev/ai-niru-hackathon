#!/bin/bash
# Startup hook — runs inside the Determined experiment container
# before the training entrypoint. Installs project dependencies.

set -e

pip install --quiet determined

# Install training requirements from project root
if [ -f training/requirements.txt ]; then
    pip install --quiet -r training/requirements.txt
else
    echo "WARNING: training/requirements.txt not found, installing core deps"
    pip install --quiet torch transformers accelerate peft trl datasets safetensors
fi

echo "startup-hook.sh completed successfully"
