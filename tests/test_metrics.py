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


def test_defanged_ip_and_converted_date_are_not_hallucinations():
    text = "No dia 14/03 o endereco 10[.]20[.]30[.]40 foi usado por admin"
    answer = '[{"data":"2026-03-14","ip":"10.20.30.40","usuario":"admin","arquivo":null,"hash":null}]'
    result = calculate_metrics([sample(text, answer)], [answer])
    assert result["hallucination"] == 0
    assert result["exact_match"] == 1


def test_spoken_date_is_supported():
    text = "na transcricao dia catorze ponto tres endereco 10[.]20[.]30[.]40"
    answer = '[{"data":"2026-03-14","ip":"10.20.30.40","usuario":null,"arquivo":null,"hash":null}]'
    assert calculate_metrics([sample(text, answer)], [answer])["hallucination"] == 0


def test_invented_date_is_hallucination():
    answer = '[{"data":"2026-01-01","ip":null,"usuario":null,"arquivo":null,"hash":null}]'
    expected = '[]'
    result = calculate_metrics([sample("texto sem data", expected)], [answer])
    assert result["hallucination"] == 1


def test_hallucination_counts_schema_invalid_output():
    # Registro sem a chave hash (fora do schema) e com data inventada.
    output = '[{"data":"2026-05-17","ip":null,"usuario":"admin","arquivo":null}]'
    expected = '[{"data":null,"ip":null,"usuario":"admin","arquivo":null,"hash":null}]'
    result = calculate_metrics([sample("usuario admin sem data", expected)], [output])
    assert result["schema_valid"] == 0
    assert result["micro_f1"] == 0
    assert result["hallucination"] == 0.5


def test_raw_json_object_is_not_valid_list():
    result = calculate_metrics([sample("texto", "[]")], ["{}"])
    assert result["valid_json_raw"] == 0


def test_hallucination_detected():
    answer = '[{"data":null,"ip":"10.0.0.1","usuario":null,"arquivo":null,"hash":null}]'
    expected = '[{"data":null,"ip":null,"usuario":null,"arquivo":null,"hash":null}]'
    result = calculate_metrics([sample("texto sem endereço", expected)], [answer])
    assert result["hallucination"] == 1
