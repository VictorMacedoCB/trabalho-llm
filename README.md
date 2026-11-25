# Extrator Forense de Entidades

Para uma explicação simples, consulte [GUIA_USO_APRESENTACAO.md](GUIA_USO_APRESENTACAO.md) e [VISÃO_GERAL_PARA_APRESENTAÇÃO.md](.docs/VISÃO_GERAL_PARA_APRESENTAÇÃO.md). Os documentos completos ficam em [.docs/](.docs/), incluindo o PRD original e o PRD de preparação.

Para criar e baixar os outputs do Fine-Tuned no Google Colab, consulte [COMO_FAZER_TREINO_COLAB.md](.docs/COMO_FAZER_TREINO_COLAB.md).
Para uma versão detalhada destinada a outra pessoa executar o treino, consulte [EXECUTAR_FINE_TUNED_EM_OUTRO_COMPUTADOR.md](.docs/EXECUTAR_FINE_TUNED_EM_OUTRO_COMPUTADOR.md).

Projeto em Python para extrair `data`, `ip`, `usuario`, `arquivo` e `hash` de documentos ruidosos e devolver uma lista JSON.

## Instalação

Python 3.10 a 3.12 (recomendado: Python 3.12):

```bash
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-presentation.txt
```

No Linux, ative com `source .venv/bin/activate`.

## 1. Gerar e validar o dataset

```bash
python src/data/generate_dataset.py --seed 42 --output data/raw/dataset.jsonl
python src/data/split_dataset.py --input data/raw/dataset.jsonl --output-dir data/processed --seed 42
python src/data/validate_dataset.py
```

## 2. Executar testes

```bash
python -m pytest -q
```

## 3. Treinar

Edite `configs/train.yaml` se necessário e execute:

```bash
python src/train/train_qlora.py --config configs/train.yaml
python src/train/train_qlora.py --config configs/train.yaml --compare-hparams
```

O treino espera GPU CUDA para a quantização 4-bit. Em um computador com ambiente compatível, instale as dependências completas com `python -m pip install -r requirements.txt`. Para Windows sem CUDA ou para apenas executar testes e apresentação, use `requirements-presentation.txt`. Os pesos são gravados em `outputs/adapter/` e os gráficos em `outputs/curves/`.

O notebook [train_colab.ipynb](notebooks/train_colab.ipynb) executa os mesmos passos no Colab.

## 4. Avaliação cega

Com o adaptador treinado:

```bash
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs/adapter
python src/eval/compare.py
```

Os resultados ficam em `outputs/eval/` e o relatório é gerado em `REPORT.md`.

## 5. Aplicação Streamlit

```bash
streamlit run app/streamlit_app.py
```

Backend local por padrão. Para usar um servidor HTTP compatível:

```bash
set BACKEND=http
set INFERENCE_URL=http://localhost:8000/extract
streamlit run app/streamlit_app.py
```

No PowerShell, use `$env:BACKEND="http"` e `$env:INFERENCE_URL="http://localhost:8000/extract"`.

## Variáveis de ambiente

Consulte `.env.example`. Nenhuma chave precisa ser guardada no repositório.
