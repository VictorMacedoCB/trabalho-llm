"""Interface Streamlit para o extrator forense."""

import io
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common import is_valid_ip, parse_json
from src.inference import extract

FIELDS = ["data", "ip", "usuario", "arquivo", "hash", "trecho_origem"]


def split_text(text: str, size: int = 1500) -> list[str]:
    """Divide texto por linhas, preservando duas linhas de sobreposição."""
    lines = text.splitlines()
    chunks = []
    current = ""
    overlap = []
    for line in lines:
        if len(current) + len(line) + 1 <= size:
            current = f"{current}\n{line}".strip()
        else:
            if current:
                chunks.append(current)
                overlap = current.splitlines()[-2:]
            current = "\n".join(overlap + [line]).strip()
    if current:
        chunks.append(current)
    return chunks or [text]


def read_upload(upload) -> str:
    name = upload.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(upload.getvalue()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return upload.getvalue().decode("utf-8-sig", errors="replace")


@st.cache_resource
def cached_extract(text: str, adapter: str) -> list[dict]:
    return extract(text, adapter)


st.set_page_config(page_title="Extrator Forense", layout="wide")
st.title("Extrator Forense de Entidades")

with st.sidebar:
    system = st.radio("Sistema", ["Base", "Fine-Tuned"], index=1)
    adapter = "outputs/adapter" if system == "Fine-Tuned" else ""

uploaded = st.file_uploader("Envie um documento", type=["txt", "log", "csv", "pdf"])
text_input = st.text_area("Ou cole o conteúdo aqui", height=180)
sample_name = st.selectbox(
    "Documento de exemplo",
    ["Nenhum", "relatorio.txt", "transcricao.log", "auditoria.csv"],
)

text = text_input
if uploaded is not None:
    text = read_upload(uploaded)
elif sample_name != "Nenhum":
    text = (ROOT / "data" / "samples" / sample_name).read_text(encoding="utf-8")

if st.button("Extrair entidades", type="primary") and text.strip():
    rows = []
    errors = []
    raw_outputs = []
    for chunk in split_text(text):
        try:
            records = cached_extract(chunk, adapter)
            raw_outputs.append(records)
            for record in records:
                row = {field: record.get(field) for field in FIELDS[:-1]}
                row["trecho_origem"] = chunk[:500]
                rows.append(row)
        except Exception as exc:
            try:
                records = cached_extract(chunk, adapter)
                raw_outputs.append(records)
                for record in records:
                    row = {field: record.get(field) for field in FIELDS[:-1]}
                    row["trecho_origem"] = chunk[:500]
                    rows.append(row)
            except Exception as retry_error:
                errors.append(f"Trecho não processado: {retry_error}")

    if rows:
        dataframe = pd.DataFrame(rows, columns=FIELDS)
        st.dataframe(dataframe, use_container_width=True)
        st.caption(f"Eventos: {len(dataframe)} | IPs únicos: {dataframe['ip'].nunique(dropna=True)} | "
                   f"Hashes únicos: {dataframe['hash'].nunique(dropna=True)}")

        warning_rows = []
        for row in rows:
            if row["ip"] and not is_valid_ip(row["ip"]):
                warning_rows.append("IP inválido")
            if row["hash"] and len(row["hash"]) not in (32, 40, 64):
                warning_rows.append("Hash inválido")
        if warning_rows:
            st.warning("Atenção: " + ", ".join(sorted(set(warning_rows))))

        csv_text = dataframe.to_csv(index=False, sep=",", encoding="utf-8-sig")
        st.download_button("Baixar CSV", data=csv_text, file_name="evidencias.csv", mime="text/csv")
    else:
        st.info("Nenhuma entidade encontrada.")

    for error in errors:
        st.error(error)
    with st.expander("JSON bruto"):
        st.code(__import__("json").dumps(raw_outputs, ensure_ascii=False, indent=2), language="json")
