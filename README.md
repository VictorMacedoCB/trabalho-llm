# Extrator Forense de Entidades

Extrai `data`, `ip`, `usuario`, `arquivo` e `hash` de documentos ruidosos (relatórios, transcrições, logs, e-mails) usando o modelo `Qwen/Qwen2.5-1.5B-Instruct` ajustado com QLoRA, e devolve uma lista JSON.

```text
Entrada: No dia 14/03, o IP 192.168.1.45 acessou o servidor via admin às 10:15h, baixando backup.zip
Saída:   [{"data":"2026-03-14 10:15","ip":"192.168.1.45","usuario":"admin","arquivo":"backup.zip","hash":null}]
```

## Documentação

| Arquivo | Conteúdo |
|---|---|
| `README.md` | Instalação e execução de todas as etapas (este arquivo). |
| [.docs/GUIA_COLAB_COMPLETO.md](.docs/GUIA_COLAB_COMPLETO.md) | Treino no Google Colab, passo a passo, do ZIP do projeto até o app. |
| [.docs/APRESENTACAO.md](.docs/APRESENTACAO.md) | Conceitos, métricas, roteiro de apresentação e perguntas prováveis. |
| [.docs/PRD_Extrator_Forense_Grupo2.md](.docs/PRD_Extrator_Forense_Grupo2.md) | Requisitos originais do trabalho. |
| [DECISIONS.md](DECISIONS.md) | Decisões tomadas onde o PRD era ambíguo. |
| [REPORT.md](REPORT.md) | Relatório de resultados (gerado por `compare.py`). |

## Estrutura

```text
app/streamlit_app.py        interface de demonstração
configs/train.yaml          hiperparâmetros do treino
data/processed/             train/val/test (140/30/30)
data/samples/               documentos de exemplo e planilha_teste.csv
notebooks/train_colab.ipynb treino e avaliação no Colab
src/common.py               prompt, normalização e validação
src/csv_input.py            leitura de planilhas CSV
src/inference.py            inferência (local ou HTTP)
src/data/                   geração, divisão e validação do dataset
src/train/train_qlora.py    treino LoRA/QLoRA
src/eval/                   métricas, avaliação cega e avaliação de CSV
tests/                      testes automatizados
outputs/                    adaptador, curvas e avaliação (gerado)
```

## 1. Instalação

Python 3.12 recomendado. No PowerShell, dentro da pasta do projeto:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-presentation.txt
```

- Se o PowerShell bloquear a ativação: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` e ative de novo.
- Linux/macOS: `python3.12 -m venv .venv` e `source .venv/bin/activate`.
- Python 3.13: os pins `torch==2.5.1` e `sentencepiece==0.2.0` não têm pacote pronto. Instale antes `python -m pip install torch --index-url https://download.pytorch.org/whl/cpu` e `python -m pip install "sentencepiece>=0.2.1"`, e depois os demais pacotes de `requirements-presentation.txt`.

Arquivos de dependências:

| Arquivo | Uso |
|---|---|
| `requirements-presentation.txt` | Testes, app, avaliação e treino na CPU (sem `bitsandbytes`). |
| `requirements.txt` | Ambiente completo com `bitsandbytes`, para GPU NVIDIA com Python 3.12. |
| `requirements-colab.txt` | Google Colab (usa o PyTorch que já vem no Colab). |

Na primeira execução, o modelo base (cerca de 3 GB) é baixado do Hugging Face.

## 2. Verificar

```powershell
python -m pytest -q
python src/data/validate_dataset.py
```

Esperado: `30 passed` e `Validação concluída sem erros.`

## 3. Dataset

Os arquivos de `data/processed/` já estão no repositório. Para regenerá-los (semente fixa, resultado idêntico):

```powershell
python src/data/generate_dataset.py --seed 42 --output data/raw/dataset.jsonl
python src/data/split_dataset.py --input data/raw/dataset.jsonl --output-dir data/processed --seed 42
python src/data/validate_dataset.py
```

## 4. Treino

### Opção A: Google Colab (recomendado sem GPU NVIDIA)

Siga [.docs/GUIA_COLAB_COMPLETO.md](.docs/GUIA_COLAB_COMPLETO.md). Leva cerca de 30 a 60 minutos e devolve `fine_tuned_outputs.zip` para extrair na pasta do projeto.

### Opção B: no próprio computador

O script detecta o hardware:

| Hardware | Modo | Tempo aproximado |
|---|---|---|
| GPU NVIDIA + `bitsandbytes` | `qlora` (4-bit, como no PRD) | minutos |
| GPU NVIDIA sem `bitsandbytes` | `gpu` (LoRA em meia precisão) | minutos |
| Sem GPU NVIDIA | `cpu` (LoRA em float32) | horas |

Teste rápido de 2 passos (grava em pasta separada):

```powershell
python src/train/train_qlora.py --max-steps 2 --output-dir outputs/teste_rapido/adapter
```

Treino completo, comparando LoRA r=8 e r=16 como pede o PRD (o adaptador final é o de r=16):

```powershell
python src/train/train_qlora.py --config configs/train.yaml --compare-hparams
```

Gera `outputs/adapter/`, `outputs/curves/loss.png`, `loss_r8.png`, `loss_r16.png` e `hparams.md`. Use `--mode cpu|gpu|qlora` para forçar um modo.

Referência medida em um Intel Core i7-12700 sem GPU: o teste de 2 passos levou cerca de 7 minutos; o treino completo deve levar perto de 3h30 (estimativa). No modo `cpu`, registre em `REPORT.md` que foi usado LoRA sem quantização 4-bit.

Com GPU NVIDIA no Windows, troque o torch pela versão CUDA (igual ou menor que a mostrada no `nvidia-smi`) e instale o `bitsandbytes`:

```powershell
python -m pip install --force-reinstall torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
python -m pip install bitsandbytes
```

## 5. Avaliação cega Base vs Fine-Tuned

Requer `outputs/adapter/`:

```powershell
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs\adapter
python src/eval/compare.py
```

Gera `outputs/eval/results.json`, `comparison.md`, `f1_por_entidade.png` e atualiza `REPORT.md`. Critério do PRD: Valid JSON ≥ 95% e Micro-F1 do Fine-Tuned maior que o do Base.

## 6. Teste com planilha CSV

Formato (separador `,`, `;` ou tabulação, codificação UTF-8):

```csv
texto,gabarito_json
"No dia 14/03 o IP 192.168.1.45 foi usado pelo usuario admin; arquivo backup.zip","[{""data"":""2026-03-14"",""ip"":""192.168.1.45"",""usuario"":""admin"",""arquivo"":""backup.zip"",""hash"":null}]"
"Ticket interno 88421 sem incidente","[]"
```

- Cada linha é um documento. Só a coluna `texto` vai para o modelo.
- `gabarito_json` é opcional e nunca é enviado ao modelo; quando existe, são calculadas as métricas.
- Sem a coluna `texto`, as colunas da linha são reunidas como `coluna: valor` (exemplo: `data/samples/auditoria.csv`).

Exemplo pronto com 8 linhas fictícias: `data/samples/planilha_teste.csv`.

```powershell
python src/eval/evaluate_csv.py --csv data/samples/planilha_teste.csv
python src/eval/evaluate_csv.py --csv data/samples/planilha_teste.csv --adapter outputs\adapter
```

Resultado em `outputs/eval/csv_<nome>_<sistema>.json`. Esse teste é complementar: a comparação científica do trabalho é a da seção 5. Use apenas planilhas autorizadas e sem dados pessoais.

## 7. Aplicação Streamlit

```powershell
streamlit run app/streamlit_app.py
```

1. Escolha `Base` ou `Fine-Tuned` na barra lateral (o Fine-Tuned exige `outputs/adapter/`; sem ele, o app avisa e bloqueia a extração).
2. Envie `.txt`, `.log`, `.csv` ou `.pdf`, cole um texto ou escolha um exemplo de `data/samples/`.
3. Clique em **Extrair entidades**: tabela, contadores, avisos de IP/hash inválido, **JSON bruto** e **Baixar CSV**.
4. Com um CSV que tenha `gabarito_json`, o app também mostra as métricas.

Na CPU, cada documento leva de 10 a 25 segundos.

Para usar um modelo servido em outro lugar (servidor HTTP compatível):

```powershell
$env:BACKEND="http"
$env:INFERENCE_URL="http://localhost:8000/extract"
streamlit run app/streamlit_app.py
```

Variáveis disponíveis em `.env.example`. Nenhuma chave deve ser guardada no repositório.

## 8. Problemas comuns

| Sintoma | Solução |
|---|---|
| `ModuleNotFoundError` | Ative o `.venv` e reinstale as dependências. |
| `Failed building wheel for sentencepiece` | Python mais novo que 3.12: veja a observação da seção 1 (no Colab, use `requirements-colab.txt`). |
| Fine-Tuned desabilitado no app | Falta `outputs/adapter/`: treine (seção 4) ou extraia o ZIP do Colab. |
| `Adaptador não encontrado` na avaliação | Mesmo caso acima. |
| Extração lenta | Normal na CPU. Use GPU ou o backend HTTP. |
| Aviso `Examining the path of torch.classes` no Streamlit | Aviso da integração Streamlit/PyTorch; pode ser ignorado. |
