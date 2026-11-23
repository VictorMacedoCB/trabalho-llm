# Roteiro simples de apresentação

Tempo sugerido: 8 a 12 minutos.

## 1. Objetivo

Diga:

> Nosso projeto lê documentos técnicos que podem estar incompletos ou com erros e encontra data, endereço IP, usuário, arquivo e hash. A resposta aparece em uma tabela que pode ser baixada em CSV.

## 2. Problema

Diga:

> Documentos forenses podem ser relatórios, logs, transcrições ou e-mails. Eles têm formatos diferentes e podem conter erros de digitação, IP com colchetes, datas variadas e textos sem relação com evidências.

Mostre os exemplos em `data/samples/`.

## 3. Dataset

Diga:

> Criamos 200 exemplos sintéticos. Foram usados 140 exemplos para treino, 30 para validação e 30 para teste. O teste não foi usado no treino.

Mostre:

- `data/processed/train.jsonl`
- `data/processed/val.jsonl`
- `data/processed/test.jsonl`

## 4. Modelo e QLoRA

Diga:

> Usamos o modelo Qwen 2.5 com 1,5 bilhão de parâmetros. Com QLoRA, treinamos pequenos ajustes em vez de alterar todo o modelo. Isso reduz o uso de memória.

Mostre [configs/train.yaml](configs/train.yaml).

## 5. Base e Fine-Tuned

Diga:

> O modelo Base é o modelo original. O modelo Fine-Tuned recebeu o adaptador treinado pelo projeto. Os dois recebem os mesmos textos de teste para uma comparação justa.

## 6. Métricas

Diga:

> Avaliamos se a saída é JSON válido, se respeita o formato, se encontra corretamente cada entidade e se inventa uma informação.

Principais métricas:

- Valid JSON Rate;
- Schema Valid Rate;
- Precision;
- Recall;
- F1;
- Exact Match;
- Taxa de alucinação.

## 7. Demonstrar o aplicativo

Execute:

```powershell
streamlit run app/streamlit_app.py
```

Na tela:

1. Selecione um documento de exemplo.
2. Clique em `Extrair entidades`.
3. Mostre a tabela.
4. Confira eventos, IPs únicos e hashes únicos.
5. Expanda `JSON bruto`.
6. Clique em `Baixar CSV`.
7. Compare Base e Fine-Tuned no mesmo texto.

## 8. Resultados

Não informe números que ainda não foram produzidos.

Se já houver `outputs/eval/results.json`, diga:

> Os resultados abaixo são do conjunto de teste reservado e não foram usados no treino.

Se o treinamento ainda não foi executado:

> O adaptador ainda não foi treinado no ambiente atual. Os comandos e o notebook permitem concluir o treino no Colab ou em outra máquina com GPU.

## 9. Encerramento

Diga:

> Entregamos o pipeline completo: geração e validação dos dados, treino QLoRA, avaliação entre Base e Fine-Tuned e aplicação Streamlit.

## Perguntas rápidas

### O que é alucinação?

É uma informação criada pelo modelo que não aparece no texto.

### Por que separar treino e teste?

Para verificar se o modelo aprendeu o padrão e não apenas decorou exemplos.

### Por que usar dados sintéticos?

Para controlar o gabarito e variar formatos, ruídos e tipos de documentos.

### O que é JSON?

É um formato de texto estruturado. Neste projeto, cada objeto representa um evento encontrado.

### O que é o Fine-Tuned?

É o modelo base com pequenos ajustes treinados usando nossos exemplos.

### O que acontece se o JSON estiver errado?

A avaliação registra a falha. O aplicativo tenta novamente e mostra o erro sem derrubar a página.
