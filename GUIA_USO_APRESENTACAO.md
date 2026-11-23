# Guia simples de uso e apresentação

## O que este projeto faz

O projeto recebe um documento, como relatório de incidente, conversa, log ou e-mail, e procura cinco tipos de informação:

- data;
- endereço IP;
- usuário;
- nome de arquivo;
- hash.

O resultado é mostrado em uma tabela e pode ser baixado em CSV. O projeto foi criado para a apresentação do trabalho de LLMOps em Português.

## O que cada parte representa

### 1. Dataset

Os arquivos em `data/processed/` são exemplos usados para ensinar e testar o modelo.

- `train.jsonl`: exemplos usados no treino;
- `val.jsonl`: exemplos usados para acompanhar o aprendizado;
- `test.jsonl`: exemplos reservados para a avaliação final.

O conjunto possui 200 exemplos divididos em:

- 140 para treino;
- 30 para validação;
- 30 para teste.

### 2. QLoRA

QLoRA permite ajustar um modelo grande usando poucos recursos de computador. Em vez de reprocessar todos os pesos do modelo, o projeto treina pequenos ajustes chamados de adaptadores LoRA.

O arquivo [configs/train.yaml](configs/train.yaml) guarda as configurações do treino, como modelo, número de épocas, taxa de aprendizado e tamanho do LoRA.

### 3. Modelo Base

O Modelo Base é o modelo original Qwen antes do projeto treinar o adaptador.

### 4. Modelo Fine-Tuned

O Modelo Fine-Tuned é o modelo original com o adaptador treinado pelo projeto. Ele deve aprender a devolver sempre uma lista JSON no formato solicitado.

### 5. Avaliação

Os dois modelos recebem os mesmos textos de teste. A avaliação calcula:

- se a saída é JSON válido;
- se a saída respeita o formato;
- quantas entidades foram encontradas corretamente;
- se houve alucinação;
- se a lista inteira foi igual ao gabarito.

### 6. Streamlit

O Streamlit é a tela da demonstração. A banca pode enviar um arquivo ou colar texto e alternar entre Modelo Base e Modelo Fine-Tuned.

## Passo a passo para preparar o projeto

### Passo 1: instalar Python

Instale o Python 3.10, 3.11 ou 3.12 e confirme:

```powershell
python --version
```

### Passo 2: abrir a pasta

No VS Code ou no PowerShell, entre na pasta do projeto:

```powershell
cd caminho\para\trabalho-llm
```

Se o projeto estiver em outra pasta, substitua esse caminho pelo caminho real.

### Passo 3: criar o ambiente virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se o PowerShell bloquear o comando de ativação, use o Prompt de Comando:

```bat
.venv\Scripts\activate.bat
```

### Passo 4: instalar as bibliotecas

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Passo 5: testar o projeto

```powershell
python -m pytest -q
```

O resultado esperado é `12 passed`.

## Passo a passo para gerar os dados

### Passo 6: gerar exemplos sintéticos

```powershell
python src/data/generate_dataset.py --seed 42 --output data/raw/dataset.jsonl
```

Esse comando cria 200 textos e seus gabaritos.

### Passo 7: separar treino, validação e teste

```powershell
python src/data/split_dataset.py --input data/raw/dataset.jsonl --output-dir data/processed --seed 42
```

### Passo 8: verificar o dataset

```powershell
python src/data/validate_dataset.py
```

O final esperado é:

```text
Validação concluída sem erros.
```

Esse teste verifica JSON, schema, duplicatas, vazamento entre splits e formatos dos valores.

## Passo a passo para treinar

### Passo 9: treinar com o modelo padrão

Em uma máquina com GPU CUDA:

```powershell
python src/train/train_qlora.py --config configs/train.yaml
```

Em um ambiente do Colab, use o notebook [train_colab.ipynb](notebooks/train_colab.ipynb).

### Passo 10: comparar duas configurações

```powershell
python src/train/train_qlora.py --config configs/train.yaml --compare-hparams
```

Essa opção compara LoRA com `r=8` e `r=16`.

O resultado deve gerar:

- adaptador em `outputs/adapter/`;
- curvas em `outputs/curves/loss.png`;
- histórico em `outputs/curves/log_history.json`;
- comparação em `outputs/curves/hparams.md`.

## Passo a passo para avaliar

### Passo 11: executar as predições cegas

```powershell
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs/adapter
```

Nessa etapa, os dois sistemas recebem nomes aleatórios chamados `sistema_A` e `sistema_B`. O modelo real não é revelado no arquivo de predições.

### Passo 12: revelar os resultados

```powershell
python src/eval/compare.py
```

Esse comando gera:

- `outputs/eval/results.json`;
- `outputs/eval/comparison.md`;
- `outputs/eval/f1_por_entidade.png`;
- `REPORT.md`.

## Passo a passo para apresentar o aplicativo

### Passo 13: iniciar o Streamlit

```powershell
streamlit run app/streamlit_app.py
```

O navegador deverá abrir uma página semelhante à interface local do Streamlit.

### Passo 14: usar a interface

1. Selecione um modelo na barra lateral: Base ou Fine-Tuned.
2. Faça o upload de um arquivo `.txt`, `.log`, `.csv` ou `.pdf`.
3. Também é possível escrever o texto diretamente na caixa.
4. Use um dos três documentos de exemplo disponíveis.
5. Clique em **Extrair entidades**.
6. Observe a tabela criada.
7. Confira os contadores de eventos, IPs únicos e hashes únicos.
8. Expanda **JSON bruto** para mostrar a saída do modelo.
9. Clique em **Baixar CSV** para salvar o resultado.

## Como demonstrar comparação na apresentação

Recomenda-se a seguinte ordem:

1. Abrir o exemplo `relatorio.txt`.
2. Mostrar o modelo Base.
3. Mostrar a resposta dele.
4. Selecionar Fine-Tuned.
5. Executar novamente com o mesmo texto.
6. Comparar os dois resultados.
7. Mostrar o gráfico `f1_por_entidade.png`.
8. Explicar que o texto de teste não foi usado no treino.

## Explicação curta para apresentar oralmente

> O projeto cria dados sintéticos, divide-os em treino, validação e teste e usa QLoRA para ajustar um modelo pequeno de linguagem. O modelo aprende a transformar documentos ruidosos em uma lista JSON com cinco entidades. Depois comparamos o modelo original com o modelo ajustado usando dados separados. Por fim, usamos o Streamlit para permitir que a banca envie documentos e compare os resultados.

## Fluxo técnico resumido

```text
Documento bruto
      ↓
Divisão em trechos
      ↓
SYSTEM_PROMPT único
      ↓
Modelo Base ou Modelo Fine-Tuned
      ↓
Validação da saída JSON
      ↓
Tabela de evidências
      ↓
Exportação para CSV
```

## Como resolver problemas comuns

### O Streamlit não encontra o adaptador

Confirme que existe uma pasta `outputs/adapter/`. Se ainda não fez o treino, use inicialmente o Modelo Base.

### Não existe GPU

Use o backend HTTP apontando para um servidor hospedado no Colab. Configure no PowerShell:

```powershell
$env:BACKEND="http"
$env:INFERENCE_URL="https://endereco-do-servidor/extract"
streamlit run app/streamlit_app.py
```

### A saída não é JSON

Isso é mostrado pelo projeto como falha do modelo. Não é removido silenciosamente. Os scripts de avaliação contam a saída como inválida.

### A biblioteca não instala

Confirme que o Python é 3.10 ou superior, recrie o ambiente virtual e execute:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```
