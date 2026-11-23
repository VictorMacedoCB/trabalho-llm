# PRD — Extrator Forense de Entidades em Documentos Ruidosos

Projeto LLMOps · Grupo 2 · Fine-tuning QLoRA de uma LLM para extração de entidades forenses em JSON

> **Instrução ao agente:** implemente tudo descrito abaixo em um único repositório Python. Siga a ordem da seção 12. Não pergunte detalhes já definidos aqui; onde houver ambiguidade, escolha a opção mais simples que atenda aos critérios de aceite (seção 11) e registre a decisão em `DECISIONS.md`.

## 1. Objetivo

Treinar (QLoRA/PEFT) um modelo pequeno de linguagem para ler textos técnicos ruidosos (relatórios, transcrições, logs de auditoria, e-mails de incidente) e devolver **somente JSON válido** com as entidades forenses: data/hora, IP, usuário, arquivo e hash. Comparar cientificamente o modelo Base com o Fine-Tuned e entregar um painel Streamlit onde a banca faz upload de documentos brutos e baixa uma tabela de evidências em CSV.

**Exemplo de referência**

Entrada:
```
No dia 14/03, o IP 192.168.1.45 acessou o servidor via admin às 10:15h, baixando backup.zip (hash 4a8f...)
```

Saída esperada:
```json
[{"data": "2026-03-14 10:15", "ip": "192.168.1.45", "usuario": "admin", "arquivo": "backup.zip", "hash": "4a8f..."}]
```

## 2. Escopo

**Dentro do escopo:** geração e curadoria do dataset, treino QLoRA, avaliação Base vs Fine-Tuned, app Streamlit, relatório de resultados (`REPORT.md`) e README de execução.

**Fora do escopo:** autenticação, banco de dados, deploy em nuvem paga, suporte a idiomas além de português brasileiro (com algum inglês técnico misturado), OCR de imagens.

## 3. Contrato de saída (schema)

A saída do modelo é **sempre uma lista JSON** de objetos (um objeto por evento/ocorrência encontrada). Sem texto antes ou depois, sem markdown, sem comentários.

Campos de cada objeto (todos obrigatórios; ausente = `null`):

| Campo | Tipo | Regra de normalização |
|---|---|---|
| `data` | string ou null | `YYYY-MM-DD HH:MM` (24h). Se faltar o ano, usar 2026. Se faltar a hora, usar `YYYY-MM-DD`. |
| `ip` | string ou null | IPv4 padrão. Remover defang (`192[.]168[.]1[.]45` vira `192.168.1.45`). |
| `usuario` | string ou null | Como aparece no texto, sem aspas, em minúsculas se for login. |
| `arquivo` | string ou null | Nome do arquivo com extensão. |
| `hash` | string ou null | Hexadecimal em minúsculas, completo (MD5 32, SHA-1 40 ou SHA-256 64 caracteres) quando presente no texto. |

Regras:
- Texto sem nenhuma entidade: saída `[]`.
- Duas ocorrências distintas no mesmo texto: dois objetos na lista.
- Nunca inventar valores. Se não está no texto, é `null`.
- Ruído irrelevante (saudações, números de protocolo, versões de software, IPs de exemplo claramente marcados como não relacionados) não vira entidade.

## 4. Estrutura do repositório

```
.
├── README.md
├── REPORT.md                  # gerado/preenchido na avaliação
├── DECISIONS.md
├── requirements.txt
├── .env.example
├── configs/
│   └── train.yaml
├── data/
│   ├── raw/                   # saídas brutas da geração
│   ├── processed/
│   │   ├── train.jsonl
│   │   ├── val.jsonl
│   │   └── test.jsonl
│   └── samples/               # 3 documentos de demonstração para o app
├── src/
│   ├── common.py              # SYSTEM_PROMPT, schema, normalizadores, parse_json
│   ├── data/
│   │   ├── generate_dataset.py
│   │   ├── validate_dataset.py
│   │   └── split_dataset.py
│   ├── train/
│   │   └── train_qlora.py
│   ├── eval/
│   │   ├── run_inference.py
│   │   ├── metrics.py
│   │   └── compare.py
│   └── inference.py           # camada única de inferência (avaliação + app)
├── notebooks/
│   └── train_colab.ipynb      # wrapper fino que chama train_qlora.py no Colab
├── tests/
├── outputs/
│   ├── adapter/               # pesos LoRA
│   ├── curves/                # PNGs de loss
│   └── eval/                  # predictions_*.jsonl, results.json, comparison.md
└── app/
    └── streamlit_app.py
```

O `SYSTEM_PROMPT` fica **em um único lugar** (`src/common.py`) e é reutilizado no dataset, treino, avaliação e app, para garantir consistência.

## 5. Fase A — Dataset

### 5.1 Formato
JSONL no formato ChatML, uma amostra por linha:
```json
{"messages": [
  {"role": "system", "content": "<SYSTEM_PROMPT>"},
  {"role": "user", "content": "<texto ruidoso>"},
  {"role": "assistant", "content": "[{\"data\": ..., \"ip\": ..., ...}]"}
], "meta": {"categoria": "...", "tipo_documento": "...", "ruido": ["..."]}}
```
O campo `meta` é usado só para estratificação e análise de erro; o script de treino o ignora. O conteúdo do assistant é o JSON serializado de forma compacta e determinística (ordem fixa de chaves, `ensure_ascii=False`).

### 5.2 Tamanho e divisão
- Total: **200 amostras** (mínimo aceitável 150) depois da higienização.
- Divisão estratificada por `categoria`: **70% treino (140), 15% validação (30), 15% teste (30)**.

### 5.3 Composição (balanceamento)

| Categoria | % | Descrição |
|---|---|---|
| `um_evento` | 35 | Um único evento com 3 a 5 campos presentes. |
| `multi_evento` | 30 | 2 a 3 eventos no mesmo texto. |
| `ruido_pesado` | 15 | Muito texto irrelevante, erros de digitação, quebras de linha estranhas. |
| `campos_parciais` | 10 | Faltam campos (ex.: só IP e data); o resto é `null`. |
| `sem_entidade` | 10 | Nenhuma entidade; saída `[]`. Inclui distratores como números de protocolo e versões. |

Tipos de documento (distribuir de forma equilibrada): relatório técnico de incidente, transcrição de áudio (ASR, com palavras por extenso como "ponto" e "dois pontos", sem pontuação), log de auditoria (linhas com timestamp, mistura de PT/EN), e-mail de resposta a incidente.

Tipos de ruído a cobrir: erros de OCR (`0`↔`O`, `1`↔`l`), erros de ASR, typos, datas em formatos heterogêneos (`14/03`, `14-03-2026`, `14 de março às 10h15`, `2026-03-14T10:15:00Z`), IPs com defang, hash truncado com reticências, cabeçalhos/rodapés irrelevantes, abreviações ("usr", "srv"), números de protocolo/ticket/versão que se parecem com IPs ou datas.

### 5.4 Geração (`generate_dataset.py`)
- Usar duas fontes combinadas: (a) **geradores sintéticos com templates** em Python (valores aleatórios válidos, ruído injetado por funções) para garantir gabarito 100% correto; (b) opcionalmente, **geração por LLM via API** (chave em variável de ambiente `LLM_API_KEY`) para diversificar o estilo dos textos, sempre com o gabarito produzido pelo código, nunca inferido pelo LLM.
- Se não houver chave de API, o script deve funcionar só com a fonte (a) e produzir as 200 amostras.
- Semente fixa (`--seed 42`) para reprodutibilidade.

### 5.5 Higienização (`validate_dataset.py`)
O script deve falhar (exit code 1) e listar as linhas com problema se qualquer regra for violada:
1. JSON do assistant parseável e aderente ao schema (seção 3).
2. Todo valor não nulo de `ip`, `hash`, `arquivo`, `usuario` realmente aparece (após normalização de defang/caixa) no texto de entrada.
3. Regex: IP válido (cada octeto 0–255), hash com 32/40/64 hex quando completo, data no formato normalizado.
4. Sem duplicatas exatas nem quase duplicatas (similaridade de Jaccard por tokens > 0,85).
5. Sem vazamento entre splits: nenhum IP, hash ou nome de arquivo repetido entre treino, validação e teste.
6. Contagem por categoria e por split impressa em tabela; avisar se alguma categoria divergir mais de 5 pontos percentuais do alvo.

## 6. Fase B — Treino (QLoRA)

- **Modelo base:** `Qwen/Qwen2.5-1.5B-Instruct` (padrão). Configurável para `Qwen2.5-3B-Instruct`, `Llama-3.2-3B-Instruct` ou `gemma-2-2b-it` via `configs/train.yaml`.
- **Biblioteca:** Unsloth + TRL `SFTTrainer` (fallback: `transformers` + `peft` + `bitsandbytes` se o Unsloth falhar).
- **Quantização:** 4-bit NF4, double quant, compute dtype bf16/fp16 conforme a GPU.
- **LoRA:** r=16, alpha=32, dropout=0.05, target_modules = todas as projeções lineares (q, k, v, o, gate, up, down).
- **Hiperparâmetros iniciais:** lr 2e-4, scheduler cosine, warmup 5%, 3 épocas, batch por device 2, gradient accumulation 4, max_seq_length 1024, weight_decay 0.01, seed 42.
- **Loss apenas na resposta:** usar `train_on_responses_only` (ou máscara equivalente) para não treinar sobre o prompt.
- **Monitoramento:** avaliar na validação a cada 10 passos; registrar `train_loss` e `eval_loss`; salvar `outputs/curves/loss.png` com as duas curvas e `outputs/curves/log_history.json`.
- **Melhor checkpoint:** manter o checkpoint com menor `eval_loss` e salvar o adaptador em `outputs/adapter/`.
- **Experimento de hiperparâmetros (mínimo):** rodar pelo menos 2 configurações (ex.: r=8 vs r=16, ou lr 1e-4 vs 2e-4) e salvar um comparativo de `eval_loss` final em `outputs/curves/hparams.md`.
- Tudo parametrizado por `configs/train.yaml`; o notebook Colab apenas instala dependências, monta o Drive e chama `python src/train/train_qlora.py --config configs/train.yaml`.

## 7. Fase C — Avaliação científica

### 7.1 Procedimento
- Conjunto de teste (30 amostras) nunca usado em treino nem em seleção de hiperparâmetros.
- Dois sistemas: **Base** (modelo original, sem adaptador, mesmo `SYSTEM_PROMPT`) e **Fine-Tuned** (modelo + adaptador).
- Decodificação determinística (`temperature=0`, `do_sample=False`, `max_new_tokens=256`), mesmo prompt para os dois.
- **Cegamento:** `run_inference.py` grava as predições com rótulos anônimos (`sistema_A`, `sistema_B`) em ordem aleatória, e só `compare.py` (que lê um mapeamento salvo à parte em `outputs/eval/.key.json`) revela qual é qual no relatório final.

### 7.2 Métricas (`metrics.py`)
1. **Valid JSON Rate:** % de saídas que são JSON parseável (sem pós-processamento além de remover cercas de markdown; reportar também a taxa *sem* nenhuma limpeza).
2. **Schema Valid Rate:** % de saídas JSON que seguem o schema da seção 3.
3. **Precision, Recall e F1 por entidade** (`data`, `ip`, `usuario`, `arquivo`, `hash`): cada documento gera um conjunto de tuplas `(campo, valor)` previstas e esperadas; considerar verdadeiro positivo quando a tupla bate exatamente após normalização. Saída inválida conta como zero predições (todos os esperados viram falsos negativos).
4. **Micro-F1 e Macro-F1** agregados.
5. **Exact Match por documento:** a lista inteira de objetos prevista é igual à esperada (como multiconjunto).
6. **Taxa de alucinação:** % de valores previstos que não aparecem no texto de entrada.

### 7.3 Saídas
- `outputs/eval/results.json` com todas as métricas por sistema.
- `outputs/eval/comparison.md`: tabela Base vs Fine-Tuned (linhas = métricas, colunas = sistemas) e os 10 piores erros do Fine-Tuned com entrada, esperado e previsto.
- Gráfico de barras `outputs/eval/f1_por_entidade.png`.
- `REPORT.md` preenchido automaticamente com essas tabelas e gráficos, mais seções em branco comentadas para a análise escrita do grupo.

## 8. Fase D — Aplicação (Streamlit)

`app/streamlit_app.py`:

- **Upload:** aceita `.txt`, `.log`, `.csv` (tratado como texto) e `.pdf` (extração com `pypdf`). Também há uma caixa de texto para colar conteúdo e um seletor de 3 documentos de exemplo de `data/samples/`.
- **Pré-processamento:** dividir o documento em trechos de até ~1500 caracteres, respeitando quebras de linha/parágrafo, com sobreposição pequena (1–2 linhas) para não cortar eventos.
- **Inferência:** cada trecho passa pelo modelo; o resultado é validado e as listas são concatenadas. Se a saída for JSON inválido, tentar mais uma vez e, persistindo, registrar uma linha de erro visível (não derrubar o app).
- **Resultado:** tabela (`st.dataframe`) com colunas `data, ip, usuario, arquivo, hash, trecho_origem`; contadores (nº de eventos, nº de IPs únicos, nº de hashes únicos); botão **Baixar CSV** (UTF-8 com BOM, separador vírgula).
- **Validação de apoio:** marcar com aviso visual linhas cujo IP não passe no regex ou cujo hash tenha tamanho inválido (sem remover a linha).
- **Comparação ao vivo (diferencial para a banca):** toggle na barra lateral para escolher **Base** ou **Fine-Tuned**, e expander "JSON bruto" mostrando a saída do modelo.
- **Backend de inferência** (em `src/inference.py`, interface `extract(text) -> list[dict]`): (a) local com `transformers` + `peft` (4-bit se houver CUDA; senão CPU), carregado uma vez com `st.cache_resource`; (b) endpoint HTTP compatível com OpenAI, configurado por `INFERENCE_URL`, para quando o modelo rodar no Colab/servidor com túnel. A escolha é feita por variável de ambiente `BACKEND=local|http`.
- O app deve abrir e funcionar com `streamlit run app/streamlit_app.py` seguindo apenas o README.

## 9. Requisitos não funcionais

- Python 3.10+. Dependências em `requirements.txt` com versões fixadas.
- Reprodutibilidade: seeds fixas, configs em YAML, nenhum caminho absoluto.
- Nenhuma chave de API no repositório; usar variáveis de ambiente e `.env.example`.
- Treino deve caber em uma GPU T4 (16 GB) do Colab gratuito.
- Código com type hints nas funções públicas e docstrings curtas; testes mínimos com `pytest` para normalizadores, `parse_json` e `metrics` (pelo menos 8 casos).
- Logs claros no terminal; erros com mensagem acionável.

## 10. Riscos e decisões pré-tomadas

| Risco | Decisão |
|---|---|
| Dataset pequeno causa overfitting | Monitorar `eval_loss`; menos épocas se a validação subir; variar muito os templates. |
| Modelo base já é bom e a diferença some | Manter casos difíceis (ruído pesado, defang, ASR) e a regra de saída JSON estrita; reportar também a taxa de JSON sem limpeza. |
| Unsloth falha no ambiente | Usar o fallback `transformers` + `peft` + `bitsandbytes`. |
| Sem GPU local para o app | Backend HTTP apontando para o modelo servido no Colab, ou demonstração com adaptador mesclado em CPU. |
| Vazamento treino/teste | Verificação automática na seção 5.5 (item 5). |

## 11. Critérios de aceite

1. `validate_dataset.py` passa sem erros em `train.jsonl`, `val.jsonl` e `test.jsonl`, com 150 a 200 amostras no total e divisão 70/15/15 estratificada.
2. Treino conclui em T4 e gera `outputs/adapter/`, `outputs/curves/loss.png` com curvas de treino e validação e o comparativo de ao menos 2 configurações de hiperparâmetros.
3. `compare.py` gera `results.json`, `comparison.md` e o gráfico de F1 por entidade, com avaliação cega Base vs Fine-Tuned.
4. O Fine-Tuned atinge **Valid JSON Rate ≥ 95%** e **Micro-F1 maior que o do Base**; se não atingir, o `REPORT.md` documenta a análise de erros (não maquiar resultados).
5. O app Streamlit processa os 3 documentos de exemplo, mostra a tabela e baixa o CSV corretamente, com toggle Base/Fine-Tuned funcionando.
6. `pytest` passa; README permite reproduzir dataset → treino → avaliação → app em uma máquina limpa.

## 12. Ordem de implementação

1. `src/common.py` (schema, `SYSTEM_PROMPT`, normalizadores, `parse_json`) e testes.
2. Gerador sintético de dataset, `validate_dataset.py` e `split_dataset.py`; gerar os 3 arquivos finais.
3. `src/inference.py` e `metrics.py` com testes; `run_inference.py` e `compare.py`.
4. Esqueleto do app Streamlit já funcionando com o modelo Base (permite validar a interface cedo).
5. `train_qlora.py`, `configs/train.yaml` e o notebook Colab; treinar as configurações de hiperparâmetros.
6. Rodar a avaliação cega Base vs Fine-Tuned e gerar `REPORT.md`.
7. Integrar o adaptador final no app, completar README e `DECISIONS.md`, e rodar a checklist da seção 11.
