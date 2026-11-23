"""Camada única de inferência para avaliação e aplicação."""

import os
from copy import deepcopy
from functools import lru_cache
from typing import Any

import requests

from src.common import SYSTEM_PROMPT, parse_json


def deterministic_generation_config(model: Any) -> Any:
    """Cria configuração de geração determinística sem opções de amostragem."""
    config = deepcopy(model.generation_config)
    config.max_new_tokens = 256
    config.do_sample = False
    config.temperature = 1.0
    config.top_p = 1.0
    config.top_k = 50
    config.min_p = None
    config.typical_p = 1.0
    config.epsilon_cutoff = 0.0
    config.eta_cutoff = 0.0
    return config


@lru_cache(maxsize=2)
def load_local(adapter: str = ""):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model_name = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tokenizer, model


def extract(text: str, adapter: str = "") -> list[dict[str, Any]]:
    backend = os.getenv("BACKEND", "local").lower()
    if backend == "http":
        url = os.getenv("INFERENCE_URL", "")
        if not url:
            raise RuntimeError("INFERENCE_URL não configurada. Defina BACKEND=local ou INFERENCE_URL.")
        response = requests.post(url, json={"text": text, "model": "fine-tuned" if adapter else "base"}, timeout=120)
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("output", payload.get("text", ""))
    else:
        tokenizer, model = load_local(adapter)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt")
        import torch
        if torch.cuda.is_available():
            inputs = {key: value.cuda() for key, value in inputs.items()}
        with torch.no_grad():
            output = model.generate(
                **inputs,
                generation_config=deterministic_generation_config(model),
            )
        raw = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return parse_json(raw)
