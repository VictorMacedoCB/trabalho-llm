"""Interface Streamlit para o extrator forense."""

import io
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common import FIELDS as ENTITY_FIELDS, is_valid_ip, parse_json, validate_schema
from src.csv_input import CsvDocument, csv_documents
from src.eval.evaluate_csv import to_sample
from src.eval.metrics import calculate_metrics
from src.inference import generate_raw

FIELDS = [*ENTITY_FIELDS, "trecho_origem"]
ADAPTER_DIR = ROOT / "outputs" / "adapter"


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


def build_documents(text: str, is_csv: bool) -> list[CsvDocument]:
    """CSV: um documento por linha. Demais formatos: blocos de texto."""
    if is_csv:
        try:
            return csv_documents(text)
        except Exception as exc:  # noqa: BLE001 - CSV malformado cai para texto bruto
            st.warning(f"Não foi possível ler o CSV como planilha ({exc}). O conteúdo será tratado como texto.")
    return [CsvDocument(linha=index, texto=chunk) for index, chunk in enumerate(split_text(text), 1)]


@st.cache_data(show_spinner=False)
def cached_generate(text: str, adapter: str) -> str:
    return generate_raw(text, adapter)


st.set_page_config(page_title="Extrator Forense", layout="wide")
st.title("Extrator Forense de Entidades")

adapter_available = (ADAPTER_DIR / "adapter_config.json").exists()
with st.sidebar:
    system = st.radio("Sistema", ["Base", "Fine-Tuned"], index=1 if adapter_available else 0)
    adapter = str(ADAPTER_DIR) if system == "Fine-Tuned" else ""
    if system == "Fine-Tuned" and not adapter_available:
        st.error("Adaptador não encontrado em outputs/adapter/. Treine o modelo ou use o Base.")

uploaded = st.file_uploader("Envie um documento", type=["txt", "log", "csv", "pdf"])
text_input = st.text_area("Ou cole o conteúdo aqui", height=180)
sample_name = st.selectbox(
    "Documento de exemplo",
    ["Nenhum", "relatorio.txt", "transcricao.log", "auditoria.csv", "planilha_teste.csv"],
)

text = text_input
source_name = ""
if uploaded is not None:
    text = read_upload(uploaded)
    source_name = uploaded.name
elif sample_name != "Nenhum":
    text = (ROOT / "data" / "samples" / sample_name).read_text(encoding="utf-8-sig")
    source_name = sample_name
is_csv = source_name.lower().endswith(".csv")

can_run = not (system == "Fine-Tuned" and not adapter_available)
if st.button("Extrair entidades", type="primary", disabled=not can_run) and text.strip():
    documents = build_documents(text, is_csv)
    rows, errors, raw_outputs = [], [], []
    samples, outputs = [], []
    progress = st.progress(0.0, text="Processando...")
    for position, document in enumerate(documents, 1):
        progress.progress(position / len(documents), text=f"Processando {position}/{len(documents)}")
        raw = ""
        records = None
        last_error = None
        for attempt in range(2):
            try:
                # A segunda tentativa ignora o cache (útil no backend HTTP).
                raw = cached_generate(document.texto, adapter) if attempt == 0 else generate_raw(document.texto, adapter)
                records = parse_json(raw)
                break
            except Exception as exc:  # noqa: BLE001 - registra e tenta mais uma vez
                last_error = exc
        if records is None:
            errors.append(f"Trecho {document.linha} não processado: {last_error}")
        else:
            raw_outputs.append({"trecho": document.linha, "saida": records})
            for record in records:
                if not isinstance(record, dict):
                    continue
                row = {field: record.get(field) for field in ENTITY_FIELDS}
                row["trecho_origem"] = document.texto[:500]
                rows.append(row)
        if document.gabarito is not None:
            expected = parse_json(document.gabarito)
            if validate_schema(expected):
                samples.append(to_sample(document.texto, json.dumps(expected, ensure_ascii=False)))
                outputs.append(raw)
    progress.empty()

    if rows:
        dataframe = pd.DataFrame(rows, columns=FIELDS)
        st.dataframe(dataframe, use_container_width=True)
        st.caption(f"Eventos: {len(dataframe)} | IPs únicos: {dataframe['ip'].nunique(dropna=True)} | "
                   f"Hashes únicos: {dataframe['hash'].nunique(dropna=True)}")

        warning_rows = []
        for row in rows:
            if row["ip"] and not is_valid_ip(str(row["ip"])):
                warning_rows.append("IP inválido")
            if row["hash"] and len(str(row["hash"])) not in (32, 40, 64):
                warning_rows.append("Hash inválido")
        if warning_rows:
            st.warning("Atenção: " + ", ".join(sorted(set(warning_rows))))

        csv_text = dataframe.to_csv(index=False, sep=",")
        st.download_button("Baixar CSV", data=csv_text.encode("utf-8-sig"),
                           file_name="evidencias.csv", mime="text/csv")
    else:
        st.info("Nenhuma entidade encontrada.")

    if samples:
        metrics = calculate_metrics(samples, outputs)
        st.subheader(f"Métricas contra o gabarito ({len(samples)} linhas)")
        columns = st.columns(4)
        columns[0].metric("JSON válido", f"{metrics['valid_json_clean']:.0%}")
        columns[1].metric("Micro-F1", f"{metrics['micro_f1']:.0%}")
        columns[2].metric("Exact Match", f"{metrics['exact_match']:.0%}")
        columns[3].metric("Alucinação", f"{metrics['hallucination']:.0%}")
        st.dataframe(pd.DataFrame(metrics["entity"]).T, use_container_width=True)

    for error in errors:
        st.error(error)
    with st.expander("JSON bruto"):
        st.code(json.dumps(raw_outputs, ensure_ascii=False, indent=2), language="json")
