# Como testar o projeto com uma planilha externa

Este guia distingue duas atividades:

1. demonstrar o aplicativo com documentos reais;
2. medir cientificamente a precisão do modelo.

Uma planilha sem gabarito pode demonstrar a interface. Ela não deve ser usada para afirmar que o modelo acertou ou perdeu para o Base.

## 1. Escolher uma base autorizada

Use uma planilha pública ou fornecida pelo seu grupo.

Procure uma base com pelo menos uma destas informações:

- descricoes de incidentes;
- linhas de log;
- auditoria;
- e-mails;
- relatorios;
- alertas de seguranca.

Nao use planilhas com dados pessoais, senhas, telefones, enderecos reais ou informacoes sigilosas sem autorizacao.

Fontes possíveis:

- Kaggle;
- Hugging Face;
- CERT/SEI;
- Data.gov;
- UCI Machine Learning Repository;
- Mendeley Data.

## 2. Preparar o arquivo CSV

Abra o arquivo em Excel, LibreOffice ou Google Planilhas.

O app atual le o CSV como texto bruto. O formato mais simples para demonstrar é:

```csv
texto
"No dia 14/03 o IP 192.168.1.45 foi usado pelo usuario admin; arquivo backup.zip"
"O usuario joao.silva acessou srv_01 no dia 2026-03-15"
"Ticket interno 88421 sem relacao com incidente"
```

Se a base possuir várias colunas, crie uma nova coluna chamada `texto` e reúna nelas as informações que podem ser enviadas ao modelo.

Exemplo:

```text
timestamp + mensagem + usuario + arquivo + ip
```

Exporte como `.csv`, usando separador ponto e vírgula ou vírgula. O arquivo precisa ter codificação UTF-8.

## 3. Criar o gabarito

Para medir precisão, crie uma coluna chamada `gabarito_json` ao lado de `texto`.

Exemplo:

```csv
texto,gabarito_json
"No dia 14/03 o IP 192.168.1.45 foi usado pelo usuario admin; arquivo backup.zip","[{""data"":""2026-03-14"",""ip"":""192.168.1.45"",""usuario"":""admin"",""arquivo"":""backup.zip"",""hash"":null}]"
"Ticket interno 88421 sem incidente","[]"
```

Cada gabarito deve conter uma lista JSON com todos os campos:

- `data`;
- `ip`;
- `usuario`;
- `arquivo`;
- `hash`.

Não use uma base externa sem revisar o gabarito manualmente. O modelo pode parecer bom ou ruim dependendo da qualidade dessa resposta esperada.

## 4. Testar no aplicativo

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Inicie o Streamlit:

```powershell
streamlit run app/streamlit_app.py
```

No painel:

1. escolha `Base`;
2. envie o arquivo CSV;
3. clique em `Extrair entidades`;
4. observe a tabela;
5. abra `JSON bruto`;
6. repita com `Fine-Tuned`, somente se `outputs/adapter/` existir.

O aplicativo mostra todos os textos do CSV como um documento único. Não use a coluna `gabarito_json` como entrada do modelo.

## 5. Testar um documento isolado

Para uma demonstração rápida:

1. abra o CSV no Excel;
2. copie uma linha da coluna `texto`;
3. cole na caixa `Ou cole o conteúdo aqui`;
4. clique em `Extrair entidades`.

Use duas ou três linhas:

- uma com entidades;
- uma sem entidade;
- uma com ruído;
- uma com dois eventos.

## 6. Avaliar cientificamente no projeto

O conjunto pronto para avaliação é:

```text
data/processed/test.jsonl
```

Ele possui 30 exemplos reservados e não foi usado no treino.

Antes de avaliar, existe a necessidade de um adaptador treinado em `outputs/adapter/`.

Depois do treino, execute:

```powershell
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs\adapter
python src/eval/compare.py
```

O projeto gera:

- `outputs/eval/results.json`;
- `outputs/eval/comparison.md`;
- `outputs/eval/f1_por_entidade.png`;
- `REPORT.md`.

Esses resultados são a comparação científica principal.

## 7. Adaptar uma planilha real para o formato JSONL

Para uma avaliação mais formal com dados externos, a planilha precisa ser transformada em JSONL com formato ChatML.

Cada linha deve ter o formato:

```json
{"messages":[{"role":"system","content":"<prompt>"},{"role":"user","content":"<texto>"},{"role":"assistant","content":"<lista JSON esperada>"}],"meta":{"categoria":"...","tipo_documento":"...","ruido":[]}}
```

No projeto:

1. use `src/common.py` como fonte do prompt;
2. não deixe o modelo gerar o gabarito;
3. revise cada linha manualmente;
4. divida em treino, validação e teste;
5. execute `validate_dataset.py`;
6. só então execute o treino.

Não troque o gabarito do teste depois de ver os resultados do modelo.

## 8. Como interpretar o resultado

### Demonstração no Streamlit

Mostra:

- se a interface funciona;
- se a leitura de CSV/PDF funciona;
- se o modelo devolve JSON;
- como o CSV final aparece.

Não prova sozinho que o modelo é cientificamente melhor.

### Avaliação científica

Usa:

- conjunto reservado;
- predição de Base e Fine-Tuned;
- validação JSON;
- Precision;
- Recall;
- F1;
- Exact Match;
- alucinação.

Só essa avaliação permite afirmar que o modelo melhorou.

## 9. Resultado aceito pelo PRD

O Fine-Tuned só é considerado aceitável se:

- Valid JSON Rate for maior ou igual a 95%;
- Micro-F1 do Fine-Tuned for maior que o do Base.

Se o resultado não atingir os critérios, o relatório deve registrar o erro e a análise, não esconder os números.

## 10. Lista curta antes da apresentação

- [ ] planilha autorizada;
- [ ] dados sensíveis removidos;
- [ ] coluna `texto`;
- [ ] gabarito revisado;
- [ ] CSV em UTF-8;
- [ ] ambiente ativado;
- [ ] Streamlit iniciado;
- [ ] adaptador disponível, se o Fine-Tuned for demonstrado;
- [ ] resultados reais disponíveis em `outputs/eval/results.json`.
