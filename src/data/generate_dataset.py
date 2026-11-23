"""Gera amostras sintéticas reprodutíveis para o treinamento."""

import argparse
import json
import random
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.common import SYSTEM_PROMPT, compact_json

CATEGORY_COUNTS = {
    "um_evento": 70,
    "multi_evento": 60,
    "ruido_pesado": 30,
    "campos_parciais": 20,
    "sem_entidade": 20,
}
DOCUMENT_TYPES = [
    "relatorio_tecnico",
    "transcricao_asr",
    "log_auditoria",
    "email_incidente",
]


def random_ip(rng: random.Random) -> str:
    return ".".join(str(rng.randint(1, 223)) for _ in range(4))


def random_hash(rng: random.Random, length: int) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(length))


def make_event(rng: random.Random, index: int, partial: bool = False) -> tuple[str, dict]:
    ip = random_ip(rng)
    user = rng.choice(["admin", "srv_backup", "joao.silva", "analista1", "usuario_teste"])
    filename = f"{rng.choice(['backup', 'acesso', 'evidencia', 'logs', 'relatorio'])}_{index}.zip".replace(".zip", rng.choice([".zip", ".log", ".csv", ".pdf"]))
    hash_value = random_hash(rng, rng.choice([32, 40, 64]))
    day = rng.randint(1, 28)
    hour = rng.randint(8, 22)
    minute = rng.choice([0, 5, 15, 30, 45])
    date = f"2026-{rng.randint(1, 12):02d}-{day:02d} {hour:02d}:{minute:02d}"
    record = {"data": date, "ip": ip, "usuario": user, "arquivo": filename, "hash": hash_value}
    if partial:
        record["usuario"] = rng.choice([None, user])
        record["arquivo"] = rng.choice([None, filename])
        record["hash"] = rng.choice([None, hash_value])
    return ip, record


def render_event(rng: random.Random, record: dict, doc_type: str, noisy: bool = False) -> str:
    parts = []
    date = record["data"]
    if record["data"]:
        date = date if rng.random() > 0.5 else f"{int(date[8:10])}/{'02d' if False else int(date[5:7]):02d}"
    ip = record["ip"]
    if ip and noisy and rng.random() < 0.35:
        ip = ip.replace(".", "[.]")
    if doc_type == "log_auditoria":
        parts.append(f"{record['data'] if record['data'] else 'sem_data'} src={ip or '-'} usr={record['usuario'] or '-'}")
    elif doc_type == "transcricao_asr":
        date_words = "dois mil e vinte e seis"
        if record["data"]:
            date_words = f"dia {int(record['data'][8:10])} ponto {int(record['data'][5:7])}"
        ip_words = ip.replace(".", " ponto ") if ip else "sem ip"
        ip_text = f"{ip or 'não informado'} ({ip_words})" if ip else "não informado"
        parts.append(f"na transcricao, {date_words}, o endereco {ip_text}, usuario {record['usuario'] or 'não informado'}")
    elif doc_type == "email_incidente":
        parts.append(f"Em resposta ao incidente: acesso em {date}; IP {ip or 'não informado'}; usuário {record['usuario'] or 'não informado'}")
    else:
        parts.append(f"No dia {date[:10]} às {date[11:16] if len(date) > 10 else 'hora não informada'}, o IP {ip or 'não informado'} acessou")
        if record["usuario"]:
            parts.append(f"como usuário {record['usuario']}")
    if record["arquivo"]:
        parts.append(f"arquivo {record['arquivo']}")
    if record["hash"]:
        if noisy and rng.random() < 0.25:
            parts.append(f"hash {record['hash'][:12]}...")
        else:
            parts.append(f"hash {record['hash']}")
    return " ".join(parts)


def add_noise(text: str, rng: random.Random) -> str:
    replacements = {"o": "0", "e": "3", "i": "1", "a": "@"}
    if rng.random() < 0.45:
        text = text.replace("\n", " \n ")
    if rng.random() < 0.35:
        words = text.split()
        if words:
            pos = rng.randrange(len(words))
            words[pos] = words[pos].replace("arquivo", "arquvo")
        text = " ".join(words)
    if rng.random() < 0.2:
        text = "ticket 88421 versão 3.12.1\n" + text + "\nrodape gerado automaticamente"
    return text


def generate(raw_path: Path, seed: int) -> None:
    rng = random.Random(seed)
    samples = []
    global_index = 0

    for category, count in CATEGORY_COUNTS.items():
        for item_index in range(count):
            doc_type = DOCUMENT_TYPES[(global_index + item_index) % len(DOCUMENT_TYPES)]
            if category == "sem_entidade":
                template_index = item_index % 6
                neutral = rng.choice([
                    "Mensagem destinada ao arquivo administrativo.",
                    "A equipe registrou apenas uma conferência rotineira.",
                    "Nenhuma ação técnica precisa ser extraída deste trecho.",
                    "Conteúdo mantido para contexto histórico da ocorrência.",
                ])
                context = rng.choice([
                    "A revisão foi concluída pelo setor responsável.",
                    "Não existe evidência digital anexada a esta anotação.",
                    "A informação não deve ser usada como indicador técnico.",
                    "Este registro pertence ao contexto operacional geral.",
                    "A seção não contém atividade de rede ou autenticação.",
                ])
                templates = [
                    f"Relatório geral {item_index}: ticket {88000 + item_index}, versão {1 + item_index % 5}.2.1, sem vínculo com incidente. {neutral} {context}",
                    f"Reunião encerrada {item_index}. O exemplo 192.168.{item_index % 25}.{item_index % 200} não está relacionado à investigação. {neutral} {context}",
                    f"Dados coletados em {14 + item_index % 10}/03, protocolo BR-2026-{item_index}, sem arquivos ou hashes. {neutral} {context}",
                    f"Nota informativa {item_index}: somente versão 2.{item_index}.0 e número de série SER-{item_index}, sem evidências nem ativos associados ao caso. {neutral} {context}",
                    f"Saudações. Ticket interno INC-{item_index}, data comercial 2026-12-{item_index % 28 + 1}, sem ocorrência forense. {neutral} {context}",
                    f"Resumo operacional {item_index}: no bloco citado 10.{item_index % 11}.{item_index % 12}.1 e no índice 30.{item_index % 13}, sem associação com o incidente. {neutral} {context}",
                    f"Aviso administrativo {item_index}: referência R-{item_index} não aponta para dispositivo monitorado. {neutral} {context}",
                    f"Fechamento semanal {item_index}: não há IP, usuário, arquivo ou hash nessa nota. {neutral} {context}",
                ]
                text = templates[(template_index + item_index) % len(templates)]
                record = []
            elif category == "campos_parciais":
                _, record_data = make_event(rng, global_index, partial=True)
                text = render_event(rng, record_data, doc_type, noisy=False)
                record = [record_data]
            elif category == "multi_evento":
                records = []
                texts = []
                for event_number in range(rng.randint(2, 3)):
                    _, record_data = make_event(rng, global_index * 10 + event_number)
                    records.append(record_data)
                    texts.append(render_event(rng, record_data, doc_type))
                text = " Depois registrou-se o próximo evento: ".join(texts)
                record = records
            else:
                _, record_data = make_event(rng, global_index)
                text = render_event(rng, record_data, doc_type, noisy=category == "ruido_pesado")
                if category == "ruido_pesado":
                    text = add_noise(text, rng)
                record = [record_data]

            for obj in record:
                if obj.get("data") is not None:
                    obj["data"] = obj["data"]

            samples.append({
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": compact_json(record)},
                ],
                "meta": {
                    "categoria": category,
                    "tipo_documento": doc_type,
                    "ruido": ["typos", "ocr"] if category == "ruido_pesado" else [],
                },
            })
            global_index += 1

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    with raw_path.open("w", encoding="utf-8") as handle:
        for sample in samples:
            handle.write(json.dumps(sample, ensure_ascii=False) + "\n")
    print(f"Geradas {len(samples)} amostras em {raw_path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="data/raw/dataset.jsonl")
    args = parser.parse_args()
    generate(ROOT / args.output, args.seed)


if __name__ == "__main__":
    main()
