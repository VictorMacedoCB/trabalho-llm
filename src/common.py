"""Funções compartilhadas para o extrator forense."""

import json
import re
from typing import Any, Iterable


SYSTEM_PROMPT = """Você é um extrator de entidades forenses.
Leia o texto e devolva somente uma lista JSON válida.
Cada objeto pode conter exatamente as chaves data, ip, usuario, arquivo e hash.
Use null quando o campo não estiver presente. Nunca invente valores.
Datas sem ano usam 2026 e devem ficar como YYYY-MM-DD HH:MM ou YYYY-MM-DD.
IPs devem ser IPv4 válidos, removendo defang. Usuários devem ser como aparecem no texto.
Arquivos devem incluir extensão. Hashes completos devem ter 32, 40 ou 64 caracteres hexadecimais.
Devolva [] quando não houver entidade."""

FIELDS = ("data", "ip", "usuario", "arquivo", "hash")
IP_PATTERN = re.compile(r"(?<![\d.])(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])")
HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$|^[0-9a-fA-F]{40}$|^[0-9a-fA-F]{64}$")
DATA_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2})?$")


def remove_defang(text: str) -> str:
    return text.replace("[.]", ".").replace("(.)", ".").replace("[dot]", ".").lower()


def normalize_ip(value: str) -> str:
    return remove_defang(value.strip())


def normalize_hash(value: str) -> str | None:
    clean = value.strip().lower().rstrip(".")
    if "..." in clean or clean.endswith(".."):
        return None
    clean = clean.replace(" ", "")
    return clean if HASH_PATTERN.fullmatch(clean) else None


def normalize_usuario(value: str) -> str:
    return value.strip().strip("\"'").lower()


def normalize_arquivo(value: str) -> str:
    return value.strip().strip("\"',;")


def normalize_date(value: str) -> str:
    """Normaliza formatos simples usados pelos dados e pelo app."""
    value = value.strip()
    for separator in ("-", "/"):
        match = re.fullmatch(rf"(\d{{1,2}}){re.escape(separator)}(\d{{1,2}})(?:{re.escape(separator)}(\d{{4}}))?(?:[ T](\d{{1,2}}):(\d{{2}}))?", value)
        if match:
            day, month, year, hour, minute = match.groups()
            year = year or "2026"
            if hour is not None:
                return f"{int(year):04d}-{int(month):02d}-{int(day):02d} {int(hour):02d}:{int(minute):02d}"
            return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2})[:\d]*)?Z?", value)
    if match:
        year, month, day, hour, minute = match.groups()
        if hour is not None:
            return f"{year}-{month}-{day} {hour}:{minute}"
        return f"{year}-{month}-{day}"
    return value


def parse_json(text: str) -> list[dict[str, Any]]:
    """Remove cercas de Markdown simples e retorna uma lista JSON, ou lança ValueError."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON inválido: {exc.msg}") from exc
    if not isinstance(parsed, list):
        raise ValueError("A saída deve ser uma lista JSON")
    return parsed


def normalize_record(record: dict[str, Any]) -> dict[str, str | None]:
    return {
        "data": normalize_date(record["data"]) if record.get("data") is not None else None,
        "ip": normalize_ip(record["ip"]) if record.get("ip") is not None else None,
        "usuario": normalize_usuario(record["usuario"]) if record.get("usuario") is not None else None,
        "arquivo": normalize_arquivo(record["arquivo"]) if record.get("arquivo") is not None else None,
        "hash": normalize_hash(record["hash"]) if record.get("hash") is not None else None,
    }


def is_valid_ip(value: str) -> bool:
    if not IP_PATTERN.fullmatch(value):
        return False
    return all(0 <= int(part) <= 255 for part in value.split("."))


def validate_schema(parsed: Any) -> bool:
    if not isinstance(parsed, list):
        return False
    for item in parsed:
        if not isinstance(item, dict) or set(item) != set(FIELDS):
            return False
        for field in FIELDS:
            if item[field] is not None and not isinstance(item[field], str):
                return False
        if item["ip"] is not None and not is_valid_ip(normalize_ip(item["ip"])):
            return False
        if item["hash"] is not None and HASH_PATTERN.fullmatch(item["hash"]) is None:
            return False
        if item["data"] is not None and DATA_PATTERN.fullmatch(item["data"]) is None:
            return False
    return True


def compact_json(records: Iterable[dict[str, Any]]) -> str:
    return json.dumps(list(records), ensure_ascii=False, separators=(",", ":"))
