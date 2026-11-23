from src.common import (
    compact_json,
    is_valid_ip,
    normalize_hash,
    normalize_ip,
    normalize_date,
    parse_json,
    validate_schema,
)


def test_normalize_ip():
    assert normalize_ip("192[.]168[.]1[.]45") == "192.168.1.45"


def test_validate_ip_boundaries():
    assert is_valid_ip("255.255.255.255")
    assert not is_valid_ip("256.1.1.1")


def test_normalize_hash():
    assert normalize_hash("A" * 32) == "a" * 32
    assert normalize_hash("4a8f...") is None


def test_normalize_date():
    assert normalize_date("14/03") == "2026-03-14"
    assert normalize_date("2026-03-14T10:15:00Z") == "2026-03-14 10:15"


def test_parse_json_with_markdown():
    assert parse_json("```json\n[]\n```") == []


def test_parse_json_rejects_object():
    try:
        parse_json("{}")
        assert False
    except ValueError:
        pass


def test_valid_schema():
    item = {"data": "2026-03-14 10:15", "ip": "192.168.1.45",
            "usuario": "admin", "arquivo": "backup.zip",
            "hash": "a" * 64}
    assert validate_schema([item])


def test_invalid_schema_extra_field():
    item = {"data": None, "ip": None, "usuario": None,
            "arquivo": None, "hash": None, "extra": "x"}
    assert not validate_schema([item])


def test_compact_json():
    assert compact_json([]) == "[]"
