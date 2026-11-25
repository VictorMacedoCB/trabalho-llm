# Apresentação: conceitos, roteiro e perguntas

Material para explicar o projeto. Para instalar e executar, use o [README](../README.md).

## 1. O projeto em uma frase

Um sistema que lê documentos técnicos ruidosos e usa uma LLM ajustada com QLoRA para extrair evidências digitais (data, IP, usuário, arquivo e hash) em uma lista JSON, exibida em tabela e exportável em CSV.

O trabalho compara dois sistemas:

1. **Base:** `Qwen/Qwen2.5-1.5B-Instruct` original (1,5 bilhão de parâmetros, preparado para seguir instruções).
2. **Fine-Tuned:** o mesmo modelo com um adaptador LoRA treinado nos exemplos do projeto.

A pergunta é qual dos dois devolve JSON válido com mais frequência, acerta mais entidades e inventa menos.

## 2. Como funciona

```text
Documento (txt, log, csv, pdf ou texto colado)
   ↓  CSV: uma linha por vez | demais: blocos de até ~1.500 caracteres
SYSTEM_PROMPT único (o mesmo no dataset, treino, avaliação e app)
   ↓
Modelo Base ou Fine-Tuned
   ↓
Resposta JSON → validação de schema, IP, hash e data
   ↓
Tabela, contadores, avisos e download CSV
```

O sistema não procura palavras-chave: o texto e as regras vão para a LLM, que produz a estrutura. Funções Python validam o formato depois, mas não corrigem respostas erradas.

## 3. Contrato de saída

Lista JSON. Cada objeto tem exatamente `data`, `ip`, `usuario`, `arquivo` e `hash`.

- Campo ausente: `null`. Texto sem entidades: `[]`. Dois eventos: dois objetos.
- IP com defang (`192[.]168[.]1[.]45`) vira `192.168.1.45`.
- Datas sem ano usam 2026, no formato `YYYY-MM-DD HH:MM` ou `YYYY-MM-DD`.
- Hash só completo: 32 (MD5), 40 (SHA-1) ou 64 (SHA-256) caracteres hexadecimais. Hash truncado (`4a8f...`) vira `null`.
- Nunca inventar valores.

## 4. Dataset

- 200 exemplos sintéticos gerados por templates em Python, com semente fixa 42 (reproduzível). Sem API de LLM: o gabarito sai do próprio gerador.
- Divisão estratificada: 140 treino, 30 validação, 30 teste. O teste nunca é usado no treino nem na escolha de hiperparâmetros.
- Formato ChatML: `system` (regras), `user` (documento), `assistant` (JSON esperado) e `meta` (categoria, usada só para análise).

| Categoria | Proporção | Finalidade |
|---|---:|---|
| Um evento | 35% | Documento com várias entidades |
| Múltiplos eventos | 30% | Dois ou três eventos no mesmo texto |
| Ruído pesado | 15% | Erros de digitação, OCR, defang, hash truncado |
| Campos parciais | 10% | Alguns campos ausentes |
| Sem entidade | 10% | Texto sem evidências (inclusive IPs sem relação) |

Tipos de documento: relatório técnico, transcrição ASR, log de auditoria e e-mail de incidente.

`validate_dataset.py` verifica JSON, schema, IPs (0–255), hashes, valores presentes no texto, duplicatas exatas e quase duplicatas (Jaccard > 0,85) e **vazamento**: nenhum IP, hash ou arquivo do treino reaparece em validação ou teste.

## 5. Modelo e treino

- **Fine-tuning:** ajustar o modelo com exemplos próprios. O modelo aprende o padrão de entrada e o formato de saída, não "decora dados".
- **LoRA:** em vez de atualizar 1,5 bilhão de parâmetros, treina pequenas matrizes adicionais (o adaptador, alguns MB).
- **QLoRA:** o modelo base é carregado em 4 bits (NF4, quantização dupla), reduzindo a memória. Exige GPU NVIDIA. Sem GPU, o projeto faz LoRA comum na CPU (mais lento, registrado em `DECISIONS.md`).

Hiperparâmetros (`configs/train.yaml`): lr 2e-4 com scheduler cosine e 5% de aquecimento, 3 épocas, batch 2 com acumulação 4 (lote efetivo de 8), seq. máxima 1024, weight decay 0,01, LoRA r=16, alpha=32, dropout 0,05, nas camadas `q/k/v/o_proj` e `gate/up/down_proj`. O experimento do PRD compara r=8 e r=16 (`outputs/curves/hparams.md`).

Conceitos:

- **Loss:** erro do modelo. `train_loss` nos exemplos de treino, `eval_loss` na validação.
- **Overfitting:** a perda de treino cai e a de validação sobe; o modelo decorou em vez de generalizar. O treino guarda o checkpoint de menor `eval_loss`.
- **Acumulação de gradiente:** simula lotes maiores sem exigir mais memória.

## 6. Avaliação

**Avaliação cega:** os 30 exemplos de teste passam pelos dois sistemas, gravados como `sistema_A` e `sistema_B` em ordem aleatória. Só `compare.py` revela qual é qual, evitando análise enviesada.

| Métrica | O que mede |
|---|---|
| Valid JSON (sem limpeza) | Resposta já é uma lista JSON válida. |
| Valid JSON (com limpeza) | Vira JSON válido removendo cercas como ` ```json `. |
| Schema válido | Exatamente os cinco campos, com tipos e formatos corretos. |
| Precision | Das entidades previstas, quantas estavam certas. |
| Recall | Das entidades esperadas, quantas foram encontradas. |
| F1 | Equilíbrio entre Precision e Recall (por entidade, Micro e Macro). |
| Exact Match | Documento com a lista inteira igual ao gabarito. |
| Alucinação | Valores previstos sem suporte no texto (considera defang e datas em outros formatos, inclusive em respostas fora do schema). |

Critério de aceite do PRD: Fine-Tuned com Valid JSON ≥ 95% e Micro-F1 maior que o do Base. Se não atingir, o `REPORT.md` mostra a análise de erros sem alterar números.

Referência medida com o Base, sem treino, em `planilha_teste.csv` (8 linhas fictícias): Micro-F1 44,4%, Exact Match 37,5%, alucinação 4,2%. Erros típicos: omitir a hora da data, não reconhecer IP com defang, esquecer o campo `hash`, inventar uma data.

## 7. Roteiro (8 a 12 minutos)

1. **Objetivo:** "Nosso projeto lê documentos técnicos com erros e extrai data, IP, usuário, arquivo e hash em uma tabela exportável."
2. **Problema:** mostre `data/samples/`. "Os documentos variam de formato e têm ruído: IP com colchetes, datas diferentes, textos sem evidência."
3. **Dataset:** "200 exemplos sintéticos com gabarito controlado: 140 treino, 30 validação, 30 teste nunca vistos no treino."
4. **Modelo:** mostre `configs/train.yaml`. "Qwen 2.5 com 1,5 bilhão de parâmetros; com QLoRA treinamos só um adaptador pequeno."
5. **Métricas:** JSON válido, schema, F1 por entidade, Exact Match e alucinação.
6. **Demonstração** (`streamlit run app/streamlit_app.py`):
   1. Escolha `relatorio.txt` e o sistema **Base**; clique em **Extrair entidades**.
   2. Mostre tabela, contadores e **JSON bruto**; clique em **Baixar CSV**.
   3. Troque para **Fine-Tuned** e rode o mesmo texto; compare.
   4. Mostre `planilha_teste.csv`, que exibe as métricas contra o gabarito.
   5. Mostre um texto sem entidade e um com IP em defang.
7. **Resultados:** mostre `outputs/eval/comparison.md` e `f1_por_entidade.png`. Use apenas números reais desses arquivos.
8. **Encerramento:** "Entregamos o pipeline completo: dados, treino, avaliação cega e aplicação."

Sem adaptador treinado, apresente só o Base e diga: "O treino é feito no Colab ou em máquina com GPU; os comandos e o notebook estão prontos."

## 8. Perguntas prováveis

- **O que é alucinação?** Informação criada pelo modelo que não está no texto.
- **Por que dados sintéticos?** Para controlar o gabarito e variar formatos e ruídos sem expor dados reais.
- **Por que separar treino e teste?** Para medir se o modelo generaliza, não se decorou.
- **Por que JSON?** É estruturado e vira tabela ou CSV diretamente.
- **O que é defang?** Escrever `192[.]168[.]1[.]45` para o IP não virar link ativo.
- **O que é hash?** Identificador do conteúdo de um arquivo; aceitamos MD5, SHA-1 e SHA-256 completos.
- **Por que `sistema_A` e `sistema_B`?** Para não saber qual é qual durante a análise (avaliação cega).
- **QLoRA sempre melhora?** Não necessariamente; só a avaliação no conjunto de teste responde.
- **E se o JSON vier errado?** Conta como falha nas métricas. O app tenta mais uma vez e mostra o erro sem travar.
- **O modelo "entende" o texto?** Gera respostas a partir de padrões aprendidos; não tem conhecimento forense próprio.
- **O que é LLMOps?** Práticas para preparar dados, treinar, avaliar, versionar e publicar modelos de linguagem.

## 9. Limitações

- Dataset sintético e pequeno; não representa toda a variedade de documentos reais.
- Sem OCR: PDF depende de texto extraível.
- CPU é lenta para treino e inferência.
- O modelo pode errar o JSON ou inventar entidades; não substitui revisão humana.
- Sem autenticação ou banco de dados no app.
