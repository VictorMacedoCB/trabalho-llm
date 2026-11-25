"""Avalia o extrator sobre uma planilha CSV com as colunas ``texto`` e ``gabarito_json``.

Uso:
    python src/eval/evaluate_csv.py --csv data/samples/planilha_teste.csv
    python src/eval/evaluate_csv.py --csv data/samples/planilha_teste.csv --adapter outputs/adapter
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.common import SYSTEM_PROMPT, parse_json, validate_schema
from src.csv_input import csv_documents
from src.eval.metrics import calculate_metrics


def to_sample(text: str, answer: str) -> dict:
    return {"messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
        {"role": "assistant", "content": answer},
    ]}


def evaluate(csv_path: Path, adapter: str = "", generator=None) -> dict:
    """Executa o modelo em cada linha e calcula as métricas nas linhas com gabarito."""
    if generator is None:
        from src.inference import generate_raw as generator
    documents = csv_documents(csv_path.read_text(encoding="utf-8-sig"))
    rows, samples, outputs = [], [], []
    for document in documents:
        start = time.perf_counter()
        try:
            raw = generator(document.texto, adapter)
            status = "ok"
        except Exception as exc:  # noqa: BLE001 - registra o erro e segue com as demais linhas
            raw, status = "", f"erro: {exc}"
        row = {"linha": document.linha, "texto": document.texto, "esperado": document.gabarito,
               "previsto": raw, "status": status, "segundos": round(time.perf_counter() - start, 2)}
        if document.gabarito is not None:
            expected = parse_json(document.gabarito)
            if not validate_schema(expected):
                raise ValueError(f"Linha {document.linha}: gabarito fora do schema")
            sample = to_sample(document.texto, json.dumps(expected, ensure_ascii=False))
            row_metrics = calculate_metrics([sample], [raw])
            row["exact_match"] = bool(row_metrics["exact_match"])
            samples.append(sample)
            outputs.append(raw)
        rows.append(row)
    return {
        "arquivo": str(csv_path),
        "sistema": "Fine-Tuned" if adapter else "Base",
        "linhas": len(rows),
        "linhas_com_gabarito": len(samples),
        "metricas": calculate_metrics(samples, outputs) if samples else None,
        "resultados": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True)
    parser.add_argument("--adapter", default="")
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    if args.adapter and not (Path(args.adapter) / "adapter_config.json").exists():
        raise SystemExit(f"Adaptador não encontrado em '{args.adapter}'.")

    result = evaluate(Path(args.csv), args.adapter)
    output = Path(args.output or f"outputs/eval/csv_{Path(args.csv).stem}_{result['sistema'].lower()}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    for row in result["resultados"]:
        mark = {True: "OK  ", False: "ERRO"}.get(row.get("exact_match"), "--  ")
        print(f"[{mark}] linha {row['linha']} ({row['segundos']}s) {row['status']}")
        print(f"       previsto: {row['previsto'].strip()[:300]}")
        if row["esperado"] is not None:
            print(f"       esperado: {row['esperado']}")
    metrics = result["metricas"]
    if metrics:
        print(f"\nSistema: {result['sistema']} | linhas com gabarito: {result['linhas_com_gabarito']}")
        for key in ("valid_json_raw", "valid_json_clean", "schema_valid", "micro_f1", "macro_f1",
                    "exact_match", "hallucination"):
            print(f"  {key:<17} {metrics[key]:.1%}")
        for field, values in metrics["entity"].items():
            print(f"  F1 {field:<14} {values['f1']:.1%}")
    print(f"\nResultado salvo em {output}")


if __name__ == "__main__":
    main()
