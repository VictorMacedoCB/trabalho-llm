"""Treino LoRA/QLoRA com detecção automática do hardware.

- GPU NVIDIA + bitsandbytes: QLoRA (modelo base quantizado em 4-bit).
- GPU sem bitsandbytes: LoRA com o modelo base em meia precisão.
- Sem GPU (notebook comum): LoRA na CPU, em float32. Funciona, mas é bem mais lento.
"""

import argparse
import importlib.util
import json
import logging
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def make_formatting_func(tokenizer):
    """Cria a função de formatação usada pelo SFTTrainer.

    O trl chama a função com um lote (``batched=True``) e espera uma lista de strings.
    O chat template é o mesmo usado em ``src/inference.py``, para que treino e
    inferência vejam exatamente o mesmo formato de prompt.
    """
    def format_batch(batch: dict) -> list[str]:
        conversations = batch["messages"]
        if conversations and isinstance(conversations[0], dict):
            conversations = [conversations]
        return [tokenizer.apply_chat_template(messages, tokenize=False) for messages in conversations]

    return format_batch


def detect_mode(requested: str = "auto") -> str:
    """Escolhe entre 'qlora' (GPU + 4-bit), 'gpu' (GPU sem 4-bit) e 'cpu'."""
    has_cuda = torch.cuda.is_available()
    has_bnb = importlib.util.find_spec("bitsandbytes") is not None
    if requested == "cpu" or not has_cuda:
        if requested in ("qlora", "gpu"):
            raise SystemExit("Modo solicitado exige GPU NVIDIA com CUDA, que não foi encontrada.")
        return "cpu"
    if requested == "qlora" and not has_bnb:
        raise SystemExit("Modo qlora exige o pacote bitsandbytes (pip install bitsandbytes).")
    if requested in ("qlora", "gpu"):
        return requested
    return "qlora" if has_bnb else "gpu"


def load_model(model_name: str, mode: str, use_bf16: bool):
    from transformers import AutoModelForCausalLM

    if mode == "qlora":
        from peft import prepare_model_for_kbit_training
        from transformers import BitsAndBytesConfig

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16 if use_bf16 else torch.float16,
        )
        model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb, device_map="auto")
        return prepare_model_for_kbit_training(model)
    if mode == "gpu":
        dtype = torch.bfloat16 if use_bf16 else torch.float16
        return AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=dtype, device_map="auto")
    return AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float32)


def train(config_path: str, hparams_r: int | None = None, hparams_lr: float | None = None,
          mode: str = "auto", max_steps: int = -1, output_dir: str = "outputs/adapter") -> dict:
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
    from peft import LoraConfig
    from transformers import AutoTokenizer, TrainingArguments
    from trl import SFTTrainer

    mode = detect_mode(mode)
    # Só usa bf16 com suporte nativo (Ampere+). Na T4 do Colab e nas GTX 16xx,
    # is_bf16_supported() devolve True por emulação, o que deixa o treino lento ou instável.
    use_bf16 = mode != "cpu" and torch.cuda.is_bf16_supported(including_emulation=False)
    logging.info("Modo de treino: %s | r=%s | lr=%s", mode, config["lora_r"], config["learning_rate"])
    if mode == "cpu":
        logging.warning("Sem GPU NVIDIA: treino LoRA na CPU. Espere um tempo bem maior que no Colab.")

    tokenizer = AutoTokenizer.from_pretrained(config["model_name"])
    model = load_model(config["model_name"], mode, use_bf16)
    lora = LoraConfig(
        r=config["lora_r"],
        lora_alpha=config["lora_alpha"],
        lora_dropout=config["lora_dropout"],
        target_modules=config["target_modules"],
        task_type="CAUSAL_LM",
    )
    dataset = load_dataset("json", data_files={
        "train": str(ROOT / "data" / "processed" / "train.jsonl"),
        "validation": str(ROOT / "data" / "processed" / "val.jsonl"),
    })

    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = ROOT / output_path
    output_path.mkdir(parents=True, exist_ok=True)
    curves_dir = output_path.parent / "curves"

    # Em um teste curto (--max-steps) avalia e salva a cada passo para exercitar todo o fluxo.
    step_interval = 1 if max_steps > 0 else config["eval_steps"]
    save_interval = 1 if max_steps > 0 else config["save_steps"]
    training_args = TrainingArguments(
        output_dir=str(output_path),
        num_train_epochs=config["epochs"],
        max_steps=max_steps,
        per_device_train_batch_size=config["batch_size"],
        per_device_eval_batch_size=config["batch_size"],
        gradient_accumulation_steps=config["gradient_accumulation"],
        learning_rate=config["learning_rate"],
        lr_scheduler_type=config["scheduler"],
        warmup_ratio=config["warmup_ratio"],
        weight_decay=config["weight_decay"],
        eval_strategy="steps",
        eval_steps=step_interval,
        save_strategy="steps",
        save_steps=save_interval,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        logging_steps=step_interval,
        bf16=use_bf16,
        fp16=mode != "cpu" and not use_bf16,
        use_cpu=mode == "cpu",
        report_to="none",
        seed=seed,
    )
    trainer = SFTTrainer(
        model=model,
        processing_class=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        peft_config=lora,
        formatting_func=make_formatting_func(tokenizer),
        max_seq_length=config["max_seq_length"],
        args=training_args,
    )
    start = time.perf_counter()
    trainer.train()
    elapsed = time.perf_counter() - start
    trainer.save_model(str(output_path))
    log_history = trainer.state.log_history
    curves_dir.mkdir(parents=True, exist_ok=True)
    history_text = json.dumps(log_history, ensure_ascii=False, indent=2)
    (curves_dir / "log_history.json").write_text(history_text, encoding="utf-8")
    (curves_dir / f"log_history_r{config['lora_r']}.json").write_text(history_text, encoding="utf-8")

    try:
        import matplotlib

        matplotlib.use("Agg")
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
        plt.title(f"LoRA r={config['lora_r']} ({mode})")
        plt.legend()
        plt.tight_layout()
        plt.savefig(curves_dir / "loss.png")
        plt.savefig(curves_dir / f"loss_r{config['lora_r']}.png")
        plt.close()
    except ImportError:
        logging.warning("matplotlib não disponível; gráfico não foi criado.")

    logging.info("Treino concluído em %.1f min. Adaptador salvo em %s", elapsed / 60, output_path)
    return {"r": config["lora_r"], "learning_rate": config["learning_rate"], "mode": mode,
            "minutes": round(elapsed / 60, 1), "curves_dir": str(curves_dir),
            "eval_loss": min((x["eval_loss"] for x in log_history if "eval_loss" in x), default=None)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/train.yaml")
    parser.add_argument("--compare-hparams", action="store_true",
                        help="Treina r=8 e depois r=16 (o adaptador final é o de r=16).")
    parser.add_argument("--mode", choices=["auto", "qlora", "gpu", "cpu"], default="auto",
                        help="auto detecta GPU/bitsandbytes; cpu força o treino na CPU.")
    parser.add_argument("--max-steps", type=int, default=-1,
                        help="Limita o número de passos (teste rápido). -1 usa as épocas do YAML.")
    parser.add_argument("--output-dir", default="outputs/adapter")
    args = parser.parse_args()
    experiments = [(None, None)]
    if args.compare_hparams:
        experiments = [(8, None), (16, None)]
    comparisons = []
    for r, lr in experiments:
        comparisons.append(train(args.config, hparams_r=r, hparams_lr=lr, mode=args.mode,
                                 max_steps=args.max_steps, output_dir=args.output_dir))
    if len(comparisons) > 1:
        curves_dir = Path(comparisons[-1]["curves_dir"])
        lines = ["# Comparativo de hiperparâmetros", "",
                 "| r | learning rate | modo | minutos | menor eval_loss |", "|---|---|---|---|---|"]
        for item in comparisons:
            lines.append(f"| {item['r']} | {item['learning_rate']} | {item['mode']} | {item['minutes']} | {item['eval_loss']} |")
        (curves_dir / "hparams.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
