"""Divide o dataset de forma estratificada por categoria."""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def split_dataset(input_path: Path, output_dir: Path, seed: int) -> None:
    samples = load_jsonl(input_path)
    by_category = defaultdict(list)
    for sample in samples:
        by_category[sample["meta"]["categoria"]].append(sample)

    train, val, test = [], [], []
    rng = random.Random(seed)
    for category in sorted(by_category):
        items = by_category[category][:]
        rng.shuffle(items)
        n_train = int(len(items) * 0.70)
        n_remaining = len(items) - n_train
        n_val = n_remaining // 2
        n_test = n_remaining - n_val
        train.extend(items[:n_train])
        val.extend(items[n_train:n_train + n_val])
        test.extend(items[n_train + n_val:n_train + n_val + n_test])

    # Ajuste fino para tamanhos globais exatos: 140/30/30.

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    while len(val) < 30 and test:
        val.append(test.pop())
    while len(val) > 30 and val:
        test.append(val.pop())
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("val", val), ("test", test)):
        path = output_dir / f"{name}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{name}: {len(rows)} amostras")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/dataset.jsonl")
    parser.add_argument("--output-dir", default="data/processed")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    split_dataset(Path(args.input), Path(args.output_dir), args.seed)


if __name__ == "__main__":
    main()
