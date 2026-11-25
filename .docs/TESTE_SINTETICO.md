# Como testar o projeto com dados sintéticos

Este guia mostra como usar os dados sintéticos já preparados pelo projeto.

Os dados sintéticos são textos fictícios que imitam documentos forenses. Eles não representam incidentes reais e são usados para demonstração e avaliação inicial.

## 1. Entender os dados disponíveis

O projeto possui três documentos prontos em `data/samples/`:

- `relatorio.txt`: relatório técnico;
- `transcricao.log`: transcrição ASR;
- `auditoria.csv`: log de auditoria.

Há também um conjunto científico em `data/processed/`:

- `train.jsonl`: 140 exemplos usados no treino;
- `val.jsonl`: 30 exemplos usados na validação;
- `test.jsonl`: 30 exemplos reservados para o teste.

## 2. Abrir o aplicativo

Ative o ambiente Python:

```powershell
.\.venv\Scripts\Activate.ps1
```

Inicie o Streamlit:

```powershell
streamlit run app/streamlit_app.py
```

O navegador deve abrir o painel do extrator.

Se o terminal mostrar:

```text
Examining the path of torch.classes raised ...
```

esse texto é um aviso da integração entre Streamlit e PyTorch. Ele não impede o aplicativo de abrir. Use o painel normalmente.

## 3. Testar um documento pronto

No painel:

1. abra o seletor **Documento de exemplo**;
2. selecione `relatorio.txt`;
3. clique em **Extrair entidades**;
4. confira a tabela;
5. abra o JSON bruto;
6. clique em **Baixar CSV**.

Repita com `transcricao.log` e `auditoria.csv`.

## 4. Testar texto próprio

Digite ou cole um texto na caixa **Ou cole o conteúdo aqui**.

Exemplo de um evento:

```text
No dia 14/03, o IP 192.168.1.45 acessou o servidor via admin às 10:15h,
baixando backup.zip com hash 4a8f1c2d3e4f5a6b7c8d9e0f1a2b3c4d.
```

Exemplo sem entidade:

```text
Relatório geral: ticket 88421, versão 4.2.1, sem vínculo com incidente.
```

Exemplo com dois eventos:

```text
O IP 10.20.30.40 foi usado por joao.silva às 09:30, abrindo evidencias.pdf.
Depois, o IP 172.16.8.9 foi usado por analista1 às 11:45, abrindo logs_12.log.
```

Exemplo com IP alterado:

```text
No relatório, o endereço 192[.]168[.]1[.]45 apareceu ligado ao usuário admin.
```

Clique em **Extrair entidades** após cada texto.

## 5. Criar uma planilha sintética própria

Crie um arquivo CSV com uma coluna chamada `texto`:

```csv
texto
"No dia 14/03 o IP 192.168.1.45 foi usado pelo usuario admin às 10:15h; arquivo backup.zip"
"O IP 10.20.30.40 foi usado por joao.silva em 2026-03-15"
"Ticket interno 88421, versão 4.2.1, sem incidente"
"Os sistemas 192.168.0.1 e 172.16.8.9 não estão relacionados à investigação"
"O usuario analista1 abriu evidencia.pdf em 2026-03-14 às 11:45"
```

Salve no Excel ou LibreOffice como `.csv`.

Use a opção:

- codificação UTF-8;
- separador ponto e vírgula ou vírgula;
- nomes de colunas simples.

Envie o arquivo no Streamlit em vez de enviar a planilha original do Excel.

## 6. Comparar Base e Fine-Tuned

A comparação ao vivo funciona assim:

1. selecione `Base`;
2. envie o documento sintético;
3. clique em **Extrair entidades**;
4. selecione `Fine-Tuned`;
5. envie o mesmo documento novamente;
6. compare o JSON e a tabela.

O Fine-Tuned só pode ser usado se existir o adaptador em `outputs/adapter/`.

Sem esse adaptador, apresente somente o modelo Base.

Não diga que houve melhoria no Fine-Tuned sem executar a avaliação científica.

## 7. Medir eficiência com dados sintéticos

O conjunto de teste já criado contém 30 exemplos reservados.

Com o adaptador treinado, execute:

```powershell
python src/eval/run_inference.py --test data/processed/test.jsonl --adapter outputs\adapter
python src/eval/compare.py
```

Os scripts produzem:

- `outputs/eval/results.json`;
- `outputs/eval/comparison.md`;
- `outputs/eval/f1_por_entidade.png`;
- `REPORT.md`.

As métricas podem incluir:

- Valid JSON sem limpeza;
- Valid JSON com limpeza;
- Schema Valid;
- Precision;
- Recall;
- F1 por entidade;
- Micro-F1;
- Macro-F1;
- Exact Match;
- taxa de alucinação.

## 8. Explicar os testes na apresentação

Você pode dizer:

> Os exemplos sintéticos permitem controlar o gabarito e testar formatos como IP defangado, campos ausentes, hashes truncados, datas variadas e documentos sem entidade. O conjunto de teste possui 30 exemplos que não foram utilizados no treino ou na escolha de hiperparâmetros.

Não diga que os resultados representam dados reais.

## 9. Lista rápida para apresentação

1. Ativar o ambiente.
2. Abrir o Streamlit.
3. Escolher `relatorio.txt`.
4. Mostrar o resultado.
5. Mostrar o JSON bruto.
6. Mostrar o CSV.
7. Testar um texto sem entidade.
8. Testar um texto com defang.
9. Mostrar `outputs/eval/results.json`, somente após o treino e a avaliação.
