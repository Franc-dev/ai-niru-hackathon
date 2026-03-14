"""
MentalChat-16K on Hugging Face ZeroGPU.
API: POST /api/predict with fn_index=0, data=[{messages, max_new_tokens, temperature, top_p, repetition_penalty}]
Backend adapter needed - see deploy/zerogpu/README.md.
"""
from __future__ import annotations

import gradio as gr
import spaces
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL_ID = "khazarai/MentalChat-16K"


@spaces.GPU(duration=90)
def _generate(messages: list[dict], max_new_tokens: int, temperature: float, top_p: float, repetition_penalty: float) -> str:
    """Run inference on GPU."""
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )

    prompt = tokenizer.apply_chat_template(
        [m for m in messages if (m.get("content") or "").strip()],
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    do_sample = temperature > 0

    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "do_sample": do_sample,
        "repetition_penalty": repetition_penalty,
        "pad_token_id": tokenizer.pad_token_id,
        "eos_token_id": tokenizer.eos_token_id,
    }
    if do_sample:
        gen_kwargs["temperature"] = max(temperature, 1e-5)
        gen_kwargs["top_p"] = top_p

    with torch.no_grad():
        out = model.generate(**inputs, **gen_kwargs)

    generated = out[0][inputs["input_ids"].shape[-1] :]
    return tokenizer.decode(generated, skip_special_tokens=True).strip()


def api_chat(payload: dict) -> dict:
    """Single-input API: accepts {messages, max_new_tokens, temperature, top_p, repetition_penalty}."""
    if not isinstance(payload, dict):
        return {"content": "", "model": MODEL_ID}
    messages = payload.get("messages", [])
    msgs = [{"role": m.get("role", "user"), "content": str(m.get("content", ""))} for m in messages if isinstance(m, dict)]
    if not msgs:
        return {"content": "", "model": MODEL_ID}
    content = _generate(
        messages=msgs,
        max_new_tokens=int(payload.get("max_new_tokens", 180)),
        temperature=float(payload.get("temperature", 0)),
        top_p=float(payload.get("top_p", 1.0)),
        repetition_penalty=float(payload.get("repetition_penalty", 1.08)),
    )
    return {"content": content, "model": MODEL_ID}


with gr.Blocks(title="MentalChat-16K", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# MentalChat-16K – Mental Health Support")
    gr.Markdown("API: `POST /api/predict` with `fn_index=0`, `data=[{messages, max_new_tokens, ...}]`")

    chatbot = gr.Chatbot(label="Chat")
    msg = gr.Textbox(placeholder="How are you feeling?", label="Message")
    clear = gr.Button("Clear")

    def submit(user_msg, history):
        if not user_msg.strip():
            return history, ""
        new_history = history + [(user_msg, "")]
        bot_msg = _generate(
            messages=[{"role": "user", "content": user_msg}],
            max_new_tokens=180,
            temperature=0.7,
            top_p=0.9,
            repetition_penalty=1.08,
        )
        new_history[-1] = (user_msg, bot_msg)
        return new_history, ""

    msg.submit(submit, [msg, chatbot], [chatbot, msg])
    clear.click(lambda: ([], ""), None, [chatbot, msg])

    # API endpoint for backend - fn_index 0
    gr.Interface(
        fn=api_chat,
        inputs=gr.JSON(label="payload"),
        outputs=gr.JSON(),
        api_name="v1_chat",
    )

demo.launch()
