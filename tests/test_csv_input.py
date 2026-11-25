import json
from pathlib import Path

from src.csv_input import csv_documents, detect_separator
from src.eval.evaluate_csv import evaluate

ROOT = Path(__file__).resolve().parents[1]


def test_detect_separator():
    assert detect_separator("texto;gabarito_json\na;b") == ";"
    assert detect_separator("texto,gabarito_json\na,b") == ","
    assert detect_separator("texto\nlinha, com vírgula") == ","


def test_csv_with_text_column_never_sends_answer():
    content = 'texto;gabarito_json\n"IP 10.0.0.1; usuario admin";"[]"\n"Sem entidade";"[]"\n'
    documents = csv_documents(content)
    assert [doc.texto for doc in documents] == ["IP 10.0.0.1; usuario admin", "Sem entidade"]
    assert all("gabarito" not in doc.texto and "[]" not in doc.texto for doc in documents)
    assert documents[0].gabarito == "[]"
    assert documents[0].linha == 2


def test_csv_without_text_column_joins_columns():
    content = (ROOT / "data" / "samples" / "auditoria.csv").read_text(encoding="utf-8")
    documents = csv_documents(content)
    assert len(documents) == 1
    assert documents[0].texto.startswith("timestamp: 2026-03-14T10:15:00Z | origem: 172.16.8.9")
    assert "hash:" not in documents[0].texto  # coluna vazia é omitida
    assert documents[0].gabarito is None


def test_csv_with_bom_and_blank_rows():
    content = "﻿texto\nprimeira\n\n   \nsegunda\n"
    assert [doc.texto for doc in csv_documents(content)] == ["primeira", "segunda"]


def test_sample_spreadsheet_answers_are_valid():
    documents = csv_documents((ROOT / "data" / "samples" / "planilha_teste.csv").read_text(encoding="utf-8"))
    assert len(documents) == 8
    assert all(isinstance(json.loads(doc.gabarito), list) for doc in documents)


def test_evaluate_csv_with_perfect_generator(tmp_path):
    csv_path = ROOT / "data" / "samples" / "planilha_teste.csv"
    answers = {doc.texto: doc.gabarito for doc in csv_documents(csv_path.read_text(encoding="utf-8"))}
    result = evaluate(csv_path, generator=lambda text, adapter: answers[text])
    metrics = result["metricas"]
    assert metrics["exact_match"] == 1
    assert metrics["micro_f1"] == 1
    assert metrics["hallucination"] == 0
    assert all(row["exact_match"] for row in result["resultados"])


def test_evaluate_csv_records_generator_errors():
    csv_path = ROOT / "data" / "samples" / "planilha_teste.csv"

    def broken(text, adapter):
        raise RuntimeError("sem modelo")

    result = evaluate(csv_path, generator=broken)
    assert result["metricas"]["valid_json_clean"] == 0
    assert all(row["status"].startswith("erro") for row in result["resultados"])
