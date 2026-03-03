"""
Test the trained Swahili Mental Health model.

Usage:
    python test_swahili_model.py --model-path training/artifacts/emns-swahili-mistral-v1

This script loads the trained LoRA adapter and runs inference on sample prompts.
"""

from __future__ import annotations

import argparse
import os
import json
from pathlib import Path

os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test trained Swahili model")
    parser.add_argument(
        "--model-path",
        default="training/artifacts/emns-swahili-phi3-v1",
        help="Path to trained LoRA adapter"
    )
    parser.add_argument(
        "--base-model",
        default="microsoft/Phi-3-mini-4k-instruct",
        help="Base model (must match training)"
    )
    parser.add_argument("--max-new-tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--do-sample", action="store_true", default=False)
    return parser.parse_args()


# Swahili system prompt
SYSTEM_PROMPT = """Wewe ni msaidizi wa afya ya akili (si daktari).
Jibu kwa Kiswahili sanifu pekee - USITUMIE Kiingereza hata neno moja.
Toa majibu mafupi, wazi, yenye huruma.
Toa hatua 3-6 zinazoweza kufanywa sasa.
Usitoe utambuzi wa kitabibu wala dawa.
Ikiwa swali si la afya ya akili, elekeza mazungumzo kurudi kwenye hisia au ustawi wa kihemko.
Ikiwa kuna dalili za hatari ya kujidhuru au kujiua, himiza msaada wa haraka."""


# Test prompts in Swahili
TEST_PROMPTS = [
    "Nahisi huzuni sana na sina nguvu ya kufanya chochote. Nifanyeje?",
    "Nina wasiwasi kuhusu mtihani wangu wa kesho. Nikusaidia vipi?",
    "Familia yangu hainielwi na nahisi mpweke sana.",
    "Nimechoka na kazi yangu. Msongo wa mawazo unanizidi.",
    "Napata hofu kubwa usiku na siwezi kulala vizuri.",
    "Rafiki yangu ana shida na anataka msaada, nifanyeje kumsaidia?",
]


def main() -> None:
    args = parse_args()
    
    print("=" * 60)
    print("Testing Swahili Mental Health Model")
    print("=" * 60)
    
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    
    model_path = Path(args.model_path)
    
    # Check if adapter exists
    if not model_path.exists():
        print(f"ERROR: Model path not found: {model_path}")
        print("Please train the model first using train_swahili_mistral.py")
        return
    
    # Load training config if available
    config_path = model_path / "training_config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            training_config = json.load(f)
        base_model = training_config.get("base_model", args.base_model)
        print(f"Loaded training config from {config_path}")
    else:
        base_model = args.base_model
    
    print(f"\nBase model: {base_model}")
    print(f"LoRA adapter: {model_path}")
    
    # Determine dtype
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"Compute dtype: {dtype}")
    
    # Configure quantization
    quantization_config = None
    if torch.cuda.is_available():
        try:
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
                bnb_4bit_compute_dtype=dtype,
            )
            print("Using 4-bit quantization")
        except Exception as e:
            print(f"4-bit quantization not available: {e}")
    
    # Load tokenizer
    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Load base model
    print("Loading base model...")
    model_kwargs = {
        "trust_remote_code": True,
        "torch_dtype": dtype,
        "device_map": "auto" if torch.cuda.is_available() else None,
        "low_cpu_mem_usage": True,
    }
    if quantization_config:
        model_kwargs["quantization_config"] = quantization_config
    
    model = AutoModelForCausalLM.from_pretrained(base_model, **model_kwargs)
    
    # Load LoRA adapter
    print("Loading LoRA adapter...")
    model = PeftModel.from_pretrained(model, str(model_path))
    model.eval()
    
    print("\n" + "=" * 60)
    print("Running inference on test prompts...")
    print("=" * 60)
    
    for i, prompt in enumerate(TEST_PROMPTS, 1):
        print(f"\n--- Test {i} ---")
        print(f"User: {prompt}")
        
        # Build conversation
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        # Apply chat template
        if hasattr(tokenizer, 'apply_chat_template') and tokenizer.chat_template:
            input_text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            # Mistral format fallback
            input_text = f"[INST] {SYSTEM_PROMPT}\n\n{prompt} [/INST]"
        
        # Tokenize
        inputs = tokenizer(input_text, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=args.do_sample,
                temperature=args.temperature if args.do_sample else None,
                top_p=0.9 if args.do_sample else None,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        
        # Decode response
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract assistant response (after the prompt)
        if "[/INST]" in response:
            response = response.split("[/INST]")[-1].strip()
        
        print(f"Assistant: {response}")
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
