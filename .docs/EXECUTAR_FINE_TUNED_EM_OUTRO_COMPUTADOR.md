# Executar Fine-Tuned em outro computador

Este guia serve para uma pessoa que nunca viu o projeto preparar o treinamento no Google Colab e baixar os arquivos necessários para apresentar o Fine-Tuned.

Não é necessário ter GPU no computador local.

## Resultado final esperado

Ao terminar, a pessoa deverá obter um arquivo chamado:

```text
fine_tuned_outputs.zip
```

Dentro dele devem existir:

```text
outputs/adapter/
outputs/curves/
outputs/eval/
REPORT.md
```

Esses arquivos permitem integrar o Fine-Tuned ao projeto local.

## Parte 1: obter o projeto

### Opção A: receber a pasta pelo pendrive ou nuvem

A pasta do projeto deve conter:

```text
app/
configs/
data/
notebooks/
src/
tests/
requirements.txt
README.md
```

Não é necessário enviar a pasta `.venv/`.

Não é necessário enviar arquivos de ambiente virtual.

### Opção B: GitHub

Use esta opção somente se o repositório estiver completo no GitHub.

## Parte 2: colocar o projeto no Google Drive

1. Abra o Google Drive.
2. Clique em **Novo**.
3. Selecione **Pasta**.
4. Nomeie a pasta como `trabalho-llm`.
5. Abra essa pasta.
6. Envie todos os arquivos e todas as pastas do projeto para dentro dela.

A estrutura correta no Drive deve ser:

```text
Meu Drive/
└── trabalho-llm/
    ├── app/
    ├── configs/
    ├── data/
    ├── notebooks/
    ├── src/
    ├── tests/
    ├── requirements.txt
    └── README.md
```

Dentro de `trabalho-llm`, `requirements.txt` deve aparecer diretamente.

Não coloque o projeto dentro de uma pasta aninhada como:

```text
trabalho-llm/
└── trabalho-llm/
    ├── requirements.txt
```

## Parte 3: abrir o Colab

1. Acesse https://colab.research.google.com.
2. Clique em **Arquivo**.
3. Clique em **Fazer upload do notebook**.
4. Faça upload de `notebooks/train_colab.ipynb`.

## Parte 4: ativar GPU

1. Clique em **Ambiente de execução**.
2. Clique em **Alterar tipo de ambiente de execução**.
3. Selecione:
   - **Hardware: GPU**
   - acelerador: **T4 GPU**, se estiver disponível
4. Clique em **Salvar**.
5. Reinicie o ambiente quando solicitado.

O Colab gratuito pode não oferecer T4 em todas as sessões.

## Parte 5: confirmar a GPU

Execute esta célula:

```python
import torch

print("PyTorch:", torch.__version__)
print("CUDA disponível:", torch.cuda.is_available())

if not torch.cuda.is_available():
    raise RuntimeError("Ative uma GPU T4 antes de continuar.")

print("GPU:", torch.cuda.get_device_name(0))
```

O resultado correto deve conter:

```text
CUDA disponível: True
GPU: Tesla T4
```

Se aparecer `False`, volte à configuração de ambiente e selecione uma GPU.

## Parte 6: montar o Drive

Execute:

```python
from google.colab import drive
drive.mount("/content/drive")
```

O Google solicitará autorização.

Aceite e volte ao notebook.

## Parte 7: entrar na pasta

Execute:

```python
%cd /content/drive/MyDrive/trabalho-llm
!ls
```

O comando `!ls` deve mostrar `requirements.txt`.

Se não mostrar, o projeto não está na pasta correta.

Verifique no Drive:

```text
Meu Drive/trabalho-llm/requirements.txt
```

Deve existir diretamente nessa pasta.

## Parte 8: instalar dependências

Execute:

```python
!pip install -r requirements.txt
```

Pode demorar vários minutos.

Não reinicie a sessão durante a instalação.

## Parte 9: gerar e validar os dados

Execute:

```python
!python src/data/generate_dataset.py --seed 42 --output data/raw/dataset.jsonl
!python src/data/split_dataset.py --input data/raw/dataset.jsonl --output-dir data/processed --seed 42
!python src/data/validate_dataset.py
```

O resultado final esperado é:

```text
Validação concluída sem erros.
```

## Parte 10: treinar

Execute:

```python
!python src/train/train_qlora.py --config configs/train.yaml --compare-hparams
```

O treinamento executará duas configurações:

- LoRA `r=8`;
- LoRA `r=16`.

Não feche o navegador.

Não interrompa enquanto houver logs de progresso.

Ao terminar, devem existir:

```text
outputs/adapter/
outputs/curves/loss.png
outputs/curves/log_history.json
outputs/curves/hparams.md
```

## Parte 11: avaliar Base e Fine-Tuned

Execute:

```python
!python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs/adapter
!python src/eval/compare.py
```

Ao terminar, devem existir:

```text
outputs/eval/results.json
outputs/eval/comparison.md
outputs/eval/f1_por_entidade.png
REPORT.md
```

## Parte 12: conferir os resultados

Execute:

```python
import json
from pathlib import Path

resultados = json.loads(
    Path("outputs/eval/results.json").read_text(encoding="utf-8")
)

print(json.dumps(resultados, ensure_ascii=False, indent=2))
```

Não invente valores.

Use os valores exibidos no relatório da apresentação.

## Parte 13: baixar o Fine-Tuned

Execute:

```python
!zip -r fine_tuned_outputs.zip \
  outputs/adapter \
  outputs/curves \
  outputs/eval \
  REPORT.md
```

Depois execute:

```python
from google.colab import files
files.download("fine_tuned_outputs.zip")
```

O navegador iniciará o download do arquivo:

```text
fine_tuned_outputs.zip
```

## Parte 14: integrar no outro computador

No computador usado para apresentação:

1. extraia o ZIP;
2. copie `outputs/adapter/`, `outputs/curves/`, `outputs/eval/` e `REPORT.md` para a pasta do projeto;
3. verifique que existe `outputs/adapter/`;
4. execute:

```powershell
cd caminho\para\trabalho-llm
.\.venv\Scripts\Activate.ps1
streamlit run app/streamlit_app.py
```

No painel, escolha `Fine-Tuned` na barra lateral.

## Parte 15: critério de sucesso

O Fine-Tuned está pronto somente quando existem:

- a pasta `outputs/adapter/`;
- o arquivo `outputs/eval/results.json`;
- o gráfico `outputs/eval/f1_por_entidade.png`;
- o relatório `REPORT.md`.

O PRD considera sucesso quando:

- Valid JSON Rate maior ou igual a 95%;
- Micro-F1 do Fine-Tuned maior que o do modelo Base.

Se esses critérios não forem atingidos, registre os resultados reais e não maquie os dados.

## Problemas comuns

### `requirements.txt` não encontrado

O projeto foi enviado para o lugar errado ou está dentro de outra pasta.

Volte ao Drive e confirme:

```text
Meu Drive/trabalho-llm/requirements.txt
```

### `src/data/generate_dataset.py` não encontrado

A pasta `src/` não está dentro de `trabalho-llm`.

Mova o projeto inteiro para a pasta correta.

### `CUDA disponível: False`

Troque o tipo de ambiente para GPU T4.

### A sessão terminou

Execute novamente:

```python
from google.colab import drive
drive.mount("/content/drive")
%cd /content/drive/MyDrive/trabalho-llm
```

Os outputs já enviados ao Drive podem ter sido gravados nele.

### Treino reiniciou ou terminou por limite

Salve o projeto no Drive.

No Colab gratuito, sessões podem durar pouco ou perder a conexão. Não reinicie após o limite sem salvar os arquivos já produzidos.
