from src.eval.metrics import calculate_metrics


def sample(text, answer):
    return {"messages": [
        {"role": "system", "content": "x"},
        {"role": "user", "content": text},
        {"role": "assistant", "content": answer},
    ]}


def test_exact_perfect_metrics():
    answer = '[{"data":"2026-03-14 10:15","ip":"192.168.1.45","usuario":"admin","arquivo":"backup.zip","hash":null}]'
    result = calculate_metrics([sample("192.168.1.45 admin backup.zip 2026-03-14 10:15", answer)], [answer])
    assert result["exact_match"] == 1
    assert result["valid_json_raw"] == 1
    assert result["micro_f1"] == 1


def test_invalid_json_counts_as_zero():
    answer = '[{"data":null,"ip":null,"usuario":null,"arquivo":null,"hash":null}]'
    result = calculate_metrics([sample("texto sem entidade", answer)], ["não é json"])
    assert result["valid_json_raw"] == 0
    assert result["micro_f1"] == 0


def test_hallucination_detected():
    answer = '[{"data":null,"ip":"10.0.0.1","usuario":null,"arquivo":null,"hash":null}]'
    expected = '[{"data":null,"ip":null,"usuario":null,"arquivo":null,"hash":null}]'
    result = calculate_metrics([sample("texto sem endereço", expected)], [answer])
    assert result["hallucination"] == 1
