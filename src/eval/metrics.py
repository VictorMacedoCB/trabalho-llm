"""Métricas científicas para a avaliação dos sistemas."""

from collections import Counter
from typing import Iterable

from src.common import FIELDS, normalize_record, parse_json, validate_schema


def tuples_for(record_list: list[dict]) -> set[tuple[str, str]]:
    result = set()
    for record in record_list:
        normalized = normalize_record(record)
        for field in FIELDS:
            if normalized[field] is not None:
                result.add((field, normalized[field]))
    return result


def lists_as_multiset(record_list: list[dict]) -> tuple:
    normalized = tuple(sorted(tuple((field, value) for field, value in normalize_record(record).items())
                              for record in record_list))
    return normalized


def calculate_metrics(samples: list[dict], predictions: list[str]) -> dict:
    valid_json_clean = 0
    valid_json_raw = 0
    schema_valid = 0
    exact = 0
    totals = {field: Counter() for field in FIELDS}
    hallucinated = 0
    predicted_values = 0

    for sample, raw in zip(samples, predictions):
        text = sample["messages"][1]["content"].lower()
        expected = sample["messages"][2]["content"]
        expected_records = __import__("json").loads(expected)
        parsed_clean = None
        try:
            parsed_clean = parse_json(raw)
            valid_json_clean += 1
        except ValueError:
            pass
        try:
            import json
            json.loads(raw)
            valid_json_raw += 1
        except (json.JSONDecodeError, TypeError):
            pass
        if parsed_clean is not None and validate_schema(parsed_clean):
            schema_valid += 1
        predicted_records = parsed_clean if parsed_clean is not None and validate_schema(parsed_clean) else []
        predicted_set = tuples_for(predicted_records)
        expected_set = tuples_for(expected_records)
        if predicted_set == expected_set:
            exact += 1
        for field in FIELDS:
            predicted = {value for name, value in predicted_set if name == field}
            expected = {value for name, value in expected_set if name == field}
            totals[field]["tp"] += len(predicted & expected)
            totals[field]["fp"] += len(predicted - expected)
            totals[field]["fn"] += len(expected - predicted)
        for name, value in predicted_set:
            predicted_values += 1
            if str(value).lower() not in text:
                hallucinated += 1

    entity_metrics = {}
    f1_values = []
    for field in FIELDS:
        tp = totals[field]["tp"]
        fp = totals[field]["fp"]
        fn = totals[field]["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        entity_metrics[field] = {"precision": precision, "recall": recall, "f1": f1}
        f1_values.append(f1)

    micro_tp = sum(totals[f]["tp"] for f in FIELDS)
    micro_fp = sum(totals[f]["fp"] for f in FIELDS)
    micro_fn = sum(totals[f]["fn"] for f in FIELDS)
    micro_precision = micro_tp / (micro_tp + micro_fp) if micro_tp + micro_fp else 0.0
    micro_recall = micro_tp / (micro_tp + micro_fn) if micro_tp + micro_fn else 0.0
    micro_f1 = 2 * micro_precision * micro_recall / (micro_precision + micro_recall) if micro_precision + micro_recall else 0.0
    count = len(samples)
    return {
        "valid_json_raw": valid_json_raw / count if count else 0,
        "valid_json_clean": valid_json_clean / count if count else 0,
        "schema_valid": schema_valid / count if count else 0,
        "entity": entity_metrics,
        "micro_f1": micro_f1,
        "macro_f1": sum(f1_values) / len(f1_values) if f1_values else 0,
        "exact_match": exact / count if count else 0,
        "hallucination": hallucinated / predicted_values if predicted_values else 0,
    }
