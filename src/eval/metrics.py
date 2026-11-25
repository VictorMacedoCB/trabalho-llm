"""Métricas científicas para a avaliação dos sistemas."""

import json
import re
from collections import Counter

from src.common import FIELDS, normalize_date, normalize_record, parse_json, remove_defang, validate_schema

NUMBER_WORDS = {
    "um": 1, "uma": 1, "primeiro": 1, "dois": 2, "duas": 2, "tres": 3, "três": 3, "quatro": 4,
    "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17,
    "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
}


def _date_candidates(text: str) -> set[str]:
    """Datas (YYYY-MM-DD) que aparecem no texto em formatos numéricos ou falados."""
    candidates = set()
    for match in re.findall(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{4})?", text):
        normalized = normalize_date(match)
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
            candidates.add(normalized)
    spoken = r"(\d{1,2}|[a-zçê]+(?: e [a-zçê]+)?)"
    for day, month in re.findall(rf"dia {spoken} ponto {spoken}", text):
        values = []
        for token in (day, month):
            if token.isdigit():
                values.append(int(token))
            else:
                values.append(sum(NUMBER_WORDS.get(word, 0) for word in token.split(" e ")))
        if all(values):
            candidates.add(f"2026-{values[1]:02d}-{values[0]:02d}")
    return candidates


def value_in_text(field: str, value: str, text: str) -> bool:
    """Indica se um valor previsto tem suporte no texto de entrada."""
    clean_text = remove_defang(text.lower())
    if field == "data":
        return value[:10] in _date_candidates(clean_text)
    return str(value).lower() in clean_text


def tuples_for(record_list: list[dict]) -> set[tuple[str, str]]:
    result = set()
    for record in record_list:
        normalized = normalize_record(record)
        for field in FIELDS:
            if normalized[field] is not None:
                result.add((field, normalized[field]))
    return result


def lenient_tuples(record_list: list) -> set[tuple[str, str]]:
    """Como ``tuples_for``, mas tolera registros fora do schema (chaves ausentes, extras ou não-texto)."""
    result = set()
    for record in record_list:
        if not isinstance(record, dict):
            continue
        clean = {field: record.get(field) if isinstance(record.get(field), str) else None for field in FIELDS}
        result |= tuples_for([clean])
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
        text = sample["messages"][1]["content"]
        expected = sample["messages"][2]["content"]
        expected_records = json.loads(expected)
        parsed_clean = None
        try:
            parsed_clean = parse_json(raw)
            valid_json_clean += 1
        except ValueError:
            pass
        try:
            if isinstance(json.loads(raw), list):
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
        # A alucinação considera tudo que o modelo afirmou, mesmo fora do schema:
        # descartar a saída inteira esconderia valores inventados.
        for name, value in lenient_tuples(parsed_clean or []):
            predicted_values += 1
            if not value_in_text(name, value, text):
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
