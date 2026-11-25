"""Leitura de planilhas CSV para o extrator forense.

Regras:
- separador detectado pelo cabeçalho (vírgula, ponto e vírgula ou tabulação);
- se existir a coluna ``texto``, cada linha usa somente essa coluna como entrada;
- caso contrário, as colunas da linha são reunidas como ``coluna: valor``;
- a coluna ``gabarito_json`` nunca é enviada ao modelo: ela serve apenas para avaliação.
"""

import io
from dataclasses import dataclass

import pandas as pd

TEXT_COLUMN = "texto"
ANSWER_COLUMN = "gabarito_json"


@dataclass
class CsvDocument:
    linha: int
    texto: str
    gabarito: str | None = None


def detect_separator(content: str) -> str:
    header = content.lstrip("﻿").splitlines()[0] if content.strip() else ""
    counts = {sep: header.count(sep) for sep in (",", ";", "\t")}
    best = max(counts, key=counts.get)
    return best if counts[best] else ","


def read_csv_text(content: str) -> pd.DataFrame:
    content = content.lstrip("﻿")
    dataframe = pd.read_csv(io.StringIO(content), sep=detect_separator(content), dtype=str,
                            keep_default_na=False, skipinitialspace=True)
    dataframe.columns = [str(column).strip().lower() for column in dataframe.columns]
    return dataframe


def csv_documents(content: str) -> list[CsvDocument]:
    """Converte o CSV em documentos, um por linha, separando o gabarito da entrada."""
    dataframe = read_csv_text(content)
    has_answer = ANSWER_COLUMN in dataframe.columns
    inputs = dataframe.drop(columns=[ANSWER_COLUMN], errors="ignore")
    documents = []
    for position, (_, row) in enumerate(inputs.iterrows()):
        if TEXT_COLUMN in inputs.columns:
            text = row[TEXT_COLUMN].strip()
        else:
            text = " | ".join(f"{column}: {value.strip()}" for column, value in row.items() if value.strip())
        if not text:
            continue
        answer = dataframe.iloc[position][ANSWER_COLUMN].strip() if has_answer else None
        documents.append(CsvDocument(linha=position + 2, texto=text, gabarito=answer or None))
    return documents
