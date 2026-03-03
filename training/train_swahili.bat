@echo off
echo =====================================================
echo EMNS Swahili Mental Health Model Training
echo =====================================================
echo.

REM Navigate to project root
cd /d "%~dp0.."

REM Activate the training environment
echo Activating training environment...
call training_env\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate training environment.
    echo Please run: py -3.12 -m venv training_env
    echo Then install dependencies with: pip install torch transformers peft trl datasets accelerate huggingface_hub bitsandbytes
    pause
    exit /b 1
)

echo.
echo Python: 
python --version
echo.
echo CUDA check:
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"
echo.

REM Check HuggingFace login (Mistral is a gated model)
echo Checking HuggingFace authentication...
python -c "from huggingface_hub import whoami; print(f'Logged in as: {whoami()[\"name\"]}')" 2>nul
if errorlevel 1 (
    echo.
    echo WARNING: Not logged in to HuggingFace.
    echo Mistral-7B-Instruct is a gated model that requires authentication.
    echo.
    echo Please run: python training\hf_login.py
    echo Or set HF_TOKEN environment variable.
    echo.
    set /p "continue_anyway=Continue anyway? (y/n): "
    if /i not "%continue_anyway%"=="y" (
        pause
        exit /b 1
    )
)
echo.

echo =====================================================
echo Starting Swahili model training with Mistral-7B...
echo This will take a while. Monitor GPU usage in Task Manager.
echo =====================================================
echo.

REM Run training script
python training\scripts\train_swahili_mistral.py ^
    --base-model mistralai/Mistral-7B-Instruct-v0.3 ^
    --output-dir training\artifacts\emns-swahili-mistral-v1 ^
    --num-epochs 3 ^
    --batch-size 1 ^
    --grad-accum 16 ^
    --max-seq-length 512 ^
    --lora-r 16 ^
    --lora-alpha 32 ^
    --learning-rate 2e-4 ^
    --logging-steps 10 ^
    --save-steps 100

echo.
echo =====================================================
if errorlevel 1 (
    echo Training FAILED. Check the error messages above.
) else (
    echo Training COMPLETE!
    echo Model saved to: training\artifacts\emns-swahili-mistral-v1
)
echo =====================================================
echo.

pause
