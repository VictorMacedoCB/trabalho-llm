# Como concluir Fine-Tuned, curvas e avaliação

> **Guia para executar em outro computador:** este documento não exige
> que o computador tenha GPU. Todo o treinamento será feito no Google Colab.

Este procedimento usa o notebook [train_colab.ipynb](../notebooks/train_colab.ipynb).

## O que será produzido

- `outputs/adapter/`: adaptador LoRA do Fine-Tuned;
- `outputs/curves/loss.png`: curva de treino e validação;
- `outputs/curves/log_history.json`: histórico completo;
- `outputs/curves/hparams.md`: comparação de `r=8` e `r=16`;
- `outputs/eval/results.json`: métricas Base/Fine-Tuned;
- `outputs/eval/comparison.md`: tabela e erros;
- `outputs/eval/f1_por_entidade.png`: gráfico por entidade;
- `REPORT.md`: relatório atualizado.

## Passo 1: abrir o notebook

Faça upload de [train_colab.ipynb](../notebooks/train_colab.ipynb) no Google Colab.

O projeto completo precisa estar em:

```text
/content/drive/MyDrive/trabalho-llm
```

Ou ajuste a célula do notebook para apontar para a pasta real.

## Passo 2: ativar GPU

No Colab:

1. abra `Ambiente de execução`;
2. escolha `Alterar tipo de ambiente de execução`;
3. selecione `T4 GPU`;
4. reinicie o ambiente.

A primeira célula deve mostrar `CUDA disponível: True`.

## Passo 3: colocar o projeto no Drive

Opções:

1. faça upload da pasta compactada no Drive;
2. clone o repositório no Colab;
3. conecte o Drive e execute o projeto que já estiver em `MyDrive/trabalho-llm`.

Se usar Git:

```python
%cd /content
!git clone https://github.com/VictorMacedoCB/trabalho-llm.git
%cd trabalho-llm
```

Se o projeto já estiver no Drive, a célula existente de montagem já entra nele.

## Passo 4: instalar e validar

Execute:

```text
pip install -r requirements.txt
geração do dataset
divisão dos dados
validação
```

O notebook faz isso automaticamente nas primeiras células.

## Passo 5: treinar

Execute:

```powershell
python src/train/train_qlora.py --config configs/train.yaml --compare-hparams
```

Esse comando executa pelo menos duas configurações:

- LoRA `r=8`;
- LoRA `r=16`.

O adaptador final escrito em `outputs/adapter/` corresponde à execução mais recente, no caso `r=16`.

Não encerre o ambiente enquanto o Colab estiver treinando.

## Passo 6: avaliar

Execute:

```powershell
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs/adapter
python src/eval/compare.py
```

Isso gera Base e Fine-Tuned, revela qual foi qual apenas no relatório final e calcula todas as métricas.

## Passo 7: baixar

A última célula cria:

```text
fine_tuned_outputs.zip
```

O navegador inicia o download automaticamente.

## Passo 8: integrar no Windows

Extraia o ZIP dentro da pasta do projeto.

Depois deve existir:

```text
outputs/adapter/
outputs/curves/
outputs/eval/
REPORT.md
```

Ative o ambiente e abra o app:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app/streamlit_app.py
```

Escolha `Fine-Tuned` na barra lateral.

## Requisitos mínimos do notebook

- GPU T4 ativa;
- conexão com a internet;
- projeto disponível no Colab;
- `outputs/adapter/` criado;
- conjunto `test.jsonl` disponível.

## Não faça alegações sem os arquivos

Não diga que o Fine-Tuned ficou melhor sem primeiro obter:

- `outputs/eval/results.json`;
- `outputs/eval/comparison.md`;
- `outputs/eval/f1_por_entidade.png`.

Use apenas os valores reais encontrados nesses arquivos.
