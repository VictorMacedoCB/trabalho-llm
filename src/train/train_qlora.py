"""Treino QLoRA simples com fallback para Transformers + PEFT."""

import argparse
import json
import logging
import random
from pathlib import Path

import numpy as np
import torch
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def format_sample(example: dict) -> str:
    from src.common import SYSTEM_PROMPT
    messages = example["messages"]
    # Os textos já usam o prompt correto; esta formatação mantém treino e inferência alinhados.
    return "\n".join(f"{message['role']}: {message['content']}" for message in messages)


def train(config_path: str, hparams_r: int | None = None, hparams_lr: float | None = None) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    config = load_config(config_path)
    if hparams_r:
        config["lora_r"] = hparams_r
    if hparams_lr:
        config["learning_rate"] = hparams_lr

    seed = config["seed"]
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    from datasets import load_dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from trl import SFTTrainer

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
    )
    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    model = AutoModelForCausalLM.from_pretrained(
        config["model_name"],
        quantization_config=bnb,
        device_map="auto",
    )
    model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        task_type="CAUSAL_LM",
    )
    dataset = load_dataset("json", data_files={
        "train": "data/processed/train.jsonl",
        "validation": "data/processed/val.jsonl",
    })

    output_dir = Path("outputs/adapter")
    output_dir.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config["epochs"],
        per_device_train_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation"],
        learning_rate=config["learning_rate"],
        lr_scheduler_type=config["scheduler"],
        warmup_ratio=config["warmup_ratio"],
        weight_decay=config["weight_decay"],
        eval_strategy="steps",
        eval_steps=config["eval_steps"],
        save_strategy="steps",
        save_steps=config["save_steps"],
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=config["eval_steps"],
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        report_to="none",
        seed=seed,
    )
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        peft_config=lora,
        formatting_func=format_sample,
        max_seq_length=config["max_seq_length"],
        args=training_args,
    )
    result = trainer.train()
    trainer.save_model(str(output_dir))
    log_history = trainer.state.log_history
    curves_dir = Path("outputs/curves")
    curves_dir.mkdir(parents=True, exist_ok=True)
    (curves_dir / "log_history.json").write_text(json.dumps(log_history, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        import matplotlib.pyplot as plt
        train_loss = [(x["step"], x["loss"]) for x in log_history if "loss" in x]
        eval_loss = [(x["step"], x["eval_loss"]) for x in log_history if "eval_loss" in x]
        plt.figure(figsize=(8, 5))
        if train_loss:
            plt.plot(*zip(*train_loss), label="train_loss")
        if eval_loss:
            plt.plot(*zip(*eval_loss), label="eval_loss")
        plt.xlabel("passo")
        plt.ylabel("loss")
        plt.legend()
        plt.tight_layout()
        plt.savefig(curves_dir / "loss.png")
    except ImportError:
        logging.warning("matplotlib não disponível; gráfico não foi criado.")

    return {"r": config["lora_r"], "learning_rate": config["learning_rate"], "eval_loss": min(
        (x["eval_loss"] for x in log_history if "eval_loss" in x), default=None)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--compare-hparams", action="store_true")
    args = parser.parse_args()
    experiments = [(None, None)]
    if args.compare_hparams:
        experiments = [(8, None), (16, None)]
    comparisons = []
    for r, lr in experiments:
        comparisons.append(train(args.config, hparams_r=r, hparams_lr=lr))
    if len(comparisons) > 1:
        Path("outputs/curves").mkdir(parents=True, exist_ok=True)
        lines = ["# Comparativo de hiperparâmetros", "", "| r | learning rate | eval_loss final |", "|---|---|---|"]
        for item in comparisons:
            lines.append(f"| {item['r']} | {item['learning_rate']} | {item['eval_loss']} |")
        Path("outputs/curves/hparams.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
