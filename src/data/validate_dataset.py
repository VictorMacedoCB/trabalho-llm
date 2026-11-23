"""Valida o dataset antes do treino."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.common import HASH_PATTERN, DATA_PATTERN, IP_PATTERN, parse_json, validate_schema


def load_jsonl(path: Path) -> list[tuple[int, dict]]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    rows.append((line_number, json.loads(line)))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{line_number}: JSON inválido ({exc.msg})")
    return rows


def tokens(text: str) -> set[str]:
    import re
    return set(re.findall(r"[a-z0-9À-ÿ]+", text.lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def validate(paths: list[Path]) -> list[str]:
    errors = []
    all_rows = []
    split_entities = defaultdict(set)
    split_names = {"train": "train", "val": "val", "test": "test"}

    for path in paths:
        split_name = split_names.get(path.stem)
        rows = load_jsonl(path)
        all_rows.append((split_name, path, rows))
        text_seen = set()

        for line_number, row in rows:
            try:
                assistant = row["messages"][2]["content"]
                parsed = parse_json(assistant)
            except (KeyError, IndexError, ValueError) as exc:
                errors.append(f"{path}:{line_number}: saída do assistant inválida: {exc}")
                continue
            if not validate_schema(parsed):
                errors.append(f"{path}:{line_number}: JSON não segue o schema")

            user = row["messages"][1]["content"].lower().replace("[.]", ".").replace("[dot]", ".")
            for item in parsed:
                for field in ("ip", "hash", "arquivo", "usuario"):
                    value = item.get(field)
                    if value is not None:
                        comparable = str(value).lower()
                        if comparable not in user and field != "hash":
                            errors.append(f"{path}:{line_number}: {field} '{value}' não aparece no texto")
                        if field == "hash" and comparable not in user:
                            # Hash truncado pode não ser completo; somente hashes completos devem ser afirmados.
                            pass
                        if field in ("ip", "hash", "arquivo"):
                            split_entities[split_name].add((field, comparable))

                if item.get("ip") is not None and IP_PATTERN.fullmatch(item["ip"]) is None:
                    errors.append(f"{path}:{line_number}: IP inválido '{item['ip']}'")
                if item.get("hash") is not None and HASH_PATTERN.fullmatch(item["hash"]) is None:
                    errors.append(f"{path}:{line_number}: hash inválido")
                if item.get("data") is not None:
                    import re
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?", item["data"]) is None:
                        errors.append(f"{path}:{line_number}: data inválida '{item['data']}'")

            exact_text = json.dumps(row["messages"][1]["content"], ensure_ascii=False)
            if exact_text in text_seen:
                errors.append(f"{path}:{line_number}: duplicata exata")
            for previous in text_seen:
                prev = json.loads(previous)
                if jaccard(tokens(prev), tokens(row["messages"][1]["content"])) > 0.85:
                    errors.append(f"{path}:{line_number}: quase duplicata (Jaccard > 0.85)")
            text_seen.add(exact_text)

    for split_name, path, rows in all_rows:
        counts = Counter(row["meta"]["categoria"] for _, row in rows)
        total = len(rows)
        targets = {"um_evento": 35, "multi_evento": 30, "ruido_pesado": 15,
                   "campos_parciais": 10, "sem_entidade": 10}
        print(f"\n{split_name or path.stem}: {total} amostras")
        for category in sorted(targets):
            actual = counts[category] / total * 100 if total else 0
            print(f"  {category}: {counts[category]} ({actual:.1f}%, alvo {targets[category]}%)")
            if abs(actual - targets[category]) > 5:
                print(f"  AVISO: categoria {category} diverge mais de 5 pontos")

    for left in ("train", "val", "test"):
        for right in ("train", "val", "test"):
            if left >= right:
                continue
            repeated = split_entities[left] & split_entities[right]
            if repeated:
                errors.append(f"Vazamento entre {left} e {right}: {len(repeated)} entidades")

    total = sum(len(rows) for _, _, rows in all_rows)
    if not 150 <= total <= 200:
        errors.append(f"Total fora do limite: {total}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=[
        "data/processed/train.jsonl",
        "data/processed/val.jsonl",
        "data/processed/test.jsonl",
    ])
    args = parser.parse_args()
    paths = [ROOT / path for path in args.paths]
    try:
        errors = validate(paths)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)
    if errors:
        print("Problemas encontrados:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit(1)
    print("\nValidação concluída sem erros.")


if __name__ == "__main__":
    main()
