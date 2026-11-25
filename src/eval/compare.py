"""Revela os sistemas cegos e gera resultados, comparação e relatório."""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eval.metrics import calculate_metrics


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    eval_dir = Path("outputs/eval")
    test_samples = load_jsonl(Path("data/processed/test.jsonl"))
    key = json.loads((eval_dir / ".key.json").read_text(encoding="utf-8"))
    results = {}
    finest_worst = []

    for anonymous, real_name in key.items():
        rows = load_jsonl(eval_dir / f"predictions_{anonymous}.jsonl")
        by_index = {row["index"]: row for row in rows}
        ordered = [test_samples[index] for index in range(len(test_samples))]
        outputs = [by_index[index]["output"] if index in by_index else "" for index in range(len(test_samples))]
        metrics = calculate_metrics(ordered, outputs)
        results[real_name] = metrics

        if real_name == "Fine-Tuned":
            finest_worst = sorted(
                ({"index": row["index"], "entrada": row["text"], "esperado": row["expected"], "previsto": row["output"]}
                 for row in rows),
                key=lambda item: item["index"])[:10]

    (eval_dir / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = ["# Comparação Base vs Fine-Tuned", "",
             "| Métrica | Base | Fine-Tuned |", "|---|---:|---:|"]
    names = ("Base", "Fine-Tuned")
    metric_names = [
        ("valid_json_raw", "Valid JSON sem limpeza"),
        ("valid_json_clean", "Valid JSON com limpeza"),
        ("schema_valid", "Schema válido"),
        ("micro_f1", "Micro-F1"),
        ("macro_f1", "Macro-F1"),
        ("exact_match", "Exact Match"),
        ("hallucination", "Taxa de alucinação"),
    ]
    for key_name, label in metric_names:
        base = results.get("Base", {}).get(key_name, 0)
        fine = results.get("Fine-Tuned", {}).get(key_name, 0)
        lines.append(f"| {label} | {base:.3%} | {fine:.3%} |")
    lines += ["", "## 10 primeiros casos do Fine-Tuned"]
    for item in finest_worst:
        lines += [f"### Caso {item['index']}", "", f"Entrada: `{item['entrada']}`",
                  f"Esperado: `{item['esperado']}`", f"Previsto: `{item['previsto']}`", ""]
    (eval_dir / "comparison.md").write_text("\n".join(lines), encoding="utf-8")

    fields = ("data", "ip", "usuario", "arquivo", "hash")
    x = list(range(len(fields)))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar([i - 0.18 for i in x],
           [results.get("Base", {}).get("entity", {}).get(f, {}).get("f1", 0) for f in fields],
           0.36, label="Base")
    ax.bar([i + 0.18 for i in x],
           [results.get("Fine-Tuned", {}).get("entity", {}).get(f, {}).get("f1", 0) for f in fields],
           0.36, label="Fine-Tuned")
    ax.set_xticks(x, fields)
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(eval_dir / "f1_por_entidade.png")

    report = ["# Relatório de resultados", "",
              "## Comparação Base vs Fine-Tuned", "",
              "\n".join(lines[3:]), "",
              "![F1 por entidade](outputs/eval/f1_por_entidade.png)", "",
              "## Análise escrita", "",
              "<!-- Complete esta seção com a interpretação do grupo. -->", "",
              "## Limitações", "", "<!-- Registre limitações e próximos passos. -->"]
    Path("REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("Resultados revelados e relatório gerado.")


if __name__ == "__main__":
    main()
