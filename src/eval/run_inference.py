"""Executa inferência cega sobre o conjunto de teste."""

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.inference import generate_raw


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", default="data/processed/test.jsonl")
    parser.add_argument("--adapter", default="outputs/adapter")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not (Path(args.adapter) / "adapter_config.json").exists():
        raise SystemExit(f"Adaptador não encontrado em '{args.adapter}'. Treine o modelo antes da avaliação cega.")
    samples = load_jsonl(Path(args.test))
    rng = random.Random(args.seed)
    order = list(range(len(samples)))
    rng.shuffle(order)
    systems = [("sistema_A", ""), ("sistema_B", args.adapter)]
    rng.shuffle(systems)
    mapping = {name: ("Base" if adapter == "" else "Fine-Tuned") for name, adapter in systems}

    output_dir = Path("outputs/eval")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / ".key.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    predictions = {}
    for name, adapter in systems:
        rows = []
        for index in order:
            sample = samples[index]
            text = sample["messages"][1]["content"]
            try:
                # Guarda a saída bruta: a limpeza e o parse ficam a cargo das métricas.
                raw_output = generate_raw(text, adapter)
                status = "ok"
            except Exception as exc:
                raw_output = ""
                status = f"erro: {exc}"
            rows.append({"index": index, "text": text, "expected": sample["messages"][2]["content"],
                         "output": raw_output, "status": status})
        path = output_dir / f"predictions_{name}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        predictions[name] = rows
    print(f"Predições cegas gravadas em {output_dir}")


if __name__ == "__main__":
    main()
