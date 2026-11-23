# Passo a passo direto

Este guia serve para executar o projeto sem conhecer o código.

## 1. Abrir a pasta

Abra o PowerShell dentro da pasta do projeto.
Uma maneira simples é clicar com o botão direito na pasta e escolher
`Abrir no Terminal`.

Confirme a pasta:

```powershell
Get-Location
```

## 2. Ativar o ambiente

```powershell
.\.venv\Scripts\Activate.ps1
python --version
```

Use Python 3.12. Se ainda não tiver o ambiente `.venv`, crie-o:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Se o PowerShell bloquear a ativação:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. Confirmar a instalação

```powershell
python -m pip check
python -m pytest -q
```

Resultado esperado: `12 passed`.

## 4. Confirmar o dataset

```powershell
python src/data/validate_dataset.py
```

Resultado esperado:

```text
Validação concluída sem erros.
```

## 5. Treinar

O treino exige GPU NVIDIA com CUDA.

Se o computador não tiver GPU NVIDIA com CUDA, use o notebook [train_colab.ipynb](notebooks/train_colab.ipynb) no Google Colab:

1. Abra o Colab.
2. Faça upload do projeto ou monte o Google Drive.
3. Instale as dependências.
4. Execute o notebook.

Se houver GPU local, execute:

```powershell
python src/train/train_qlora.py --config configs/train.yaml
```

Para comparar duas configurações:

```powershell
python src/train/train_qlora.py --config configs/train.yaml --compare-hparams
```

## 6. Avaliar

Somente depois que a pasta `outputs/adapter/` existir:

```powershell
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs\adapter
python src/eval/compare.py
```

Resultado principal: `outputs/eval/results.json`.

## 7. Abrir o painel

```powershell
streamlit run app/streamlit_app.py
```

O navegador abrirá a aplicação.

## 8. Usar o painel

1. Escolha `Base` ou `Fine-Tuned`.
2. Envie um arquivo `.txt`, `.log`, `.csv` ou `.pdf`.
3. Ou cole o texto na caixa.
4. Clique em `Extrair entidades`.
5. Confira a tabela.
6. Clique em `Baixar CSV`.

Exemplos prontos:

- `data/samples/relatorio.txt`
- `data/samples/transcricao.log`
- `data/samples/auditoria.csv`

## Solução rápida

### `ModuleNotFoundError`

Ative o ambiente e instale novamente:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Torch ausente

Use o Python do ambiente:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.__version__)"
```

### Erro de CUDA

O computador não oferece CUDA para o treino. Faça o treino no Colab ou configure um backend HTTP.
