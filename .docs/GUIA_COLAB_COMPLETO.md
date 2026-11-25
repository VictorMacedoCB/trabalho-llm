# Guia completo: treinar no Google Colab e usar no notebook

Este guia leva o projeto do seu computador até o Google Colab, treina o modelo Fine-Tuned na GPU gratuita, avalia os resultados e traz tudo de volta para o computador onde será feita a apresentação.

## Visão geral

| Onde | O que acontece |
|---|---|
| Seu computador | Compacta o projeto, sem arquivos desnecessários (cerca de 120 KB). |
| Google Drive | Guarda o projeto e os resultados, mesmo que o Colab desconecte. |
| Google Colab (GPU T4) | Instala, treina r=8 e r=16, avalia Base vs Fine-Tuned e gera o ZIP de resultados. |
| Seu computador | Recebe o adaptador treinado e roda o app Streamlit. |

Você vai precisar de:

- uma conta Google;
- espaço livre no Drive (os resultados do treino ocupam menos de 1 GB);
- o projeto no computador, com o ambiente `.venv` já configurado (ver `README.md`).

Tempo estimado no Colab: de 30 a 60 minutos no total, incluindo a instalação. É uma estimativa: o tempo real depende da GPU e da fila do Colab.

---

## Parte 1: compactar o projeto (no seu computador)

Abra o PowerShell **dentro da pasta do projeto** (a pasta que contém `requirements.txt`). Uma forma simples: abra a pasta no Explorador de Arquivos, clique com o botão direito em uma área vazia e escolha **Abrir no Terminal**.

Confirme que está na pasta certa:

```powershell
Test-Path .\requirements.txt
```

Deve mostrar `True`.

Gere o ZIP na pasta Downloads:

```powershell
tar -a -c -f "$HOME\Downloads\trabalho-llm.zip" --options hdrcharset=UTF-8 --exclude=.venv --exclude=.git --exclude=outputs --exclude=.claude --exclude=__pycache__ --exclude=.pytest_cache --exclude=.env .
```

O ponto (`.`) no final é obrigatório: ele indica "a pasta atual".

O que fica de fora e por quê:

| Excluído | Motivo |
|---|---|
| `.venv` | Ambiente Python do Windows. Tem vários GB e não funciona no Colab, que instala o próprio ambiente. |
| `.git` | Histórico do Git. Não é usado no treino. |
| `outputs` | Resultados antigos. O Colab gera resultados novos. |
| `.claude` | Configuração local do editor. |
| `__pycache__`, `.pytest_cache` | Caches gerados automaticamente pelo Python. |
| `.env` | Pode conter chaves e senhas. Nunca envie para a nuvem. |

Confira o tamanho e o conteúdo:

```powershell
"{0:N0} KB" -f ((Get-Item "$HOME\Downloads\trabalho-llm.zip").Length / 1KB)
```

```powershell
tar -tf "$HOME\Downloads\trabalho-llm.zip" | Select-String "requirements.txt|train_qlora|\.venv"
```

Resultado esperado: algo perto de 120 KB, e o segundo comando mostra `requirements.txt` e `train_qlora.py`, sem nenhuma linha com `.venv`.

---

## Parte 2: enviar o ZIP para o Google Drive

1. Acesse drive.google.com.
2. Clique em **Meu Drive** (a raiz, fora de qualquer pasta).
3. Clique em **Novo > Upload de arquivo** e escolha `Downloads\trabalho-llm.zip`.

**Não descompacte no Drive.** O notebook faz isso sozinho.

O resultado deve ser:

```text
Meu Drive/
└── trabalho-llm.zip
```

Se já existir um `trabalho-llm.zip` antigo, **apague o antigo antes**. Se não apagar, o Drive salva o novo como `trabalho-llm (1).zip` e o notebook continua usando o antigo.

---

## Parte 3: abrir o notebook no Colab

1. Acesse colab.research.google.com.
2. Clique em **Arquivo > Fazer upload de notebook**.
3. Escolha, no seu computador, o arquivo `notebooks\train_colab.ipynb` da pasta do projeto.

## Parte 4: ativar a GPU

1. Clique em **Ambiente de execução > Alterar tipo de ambiente de execução**.
2. Em **Acelerador de hardware**, escolha **T4 GPU**.
3. Clique em **Salvar**.

O Colab gratuito nem sempre tem GPU disponível. Se não aparecer a opção, tente mais tarde.

---

## Parte 5: executar o notebook

Execute uma célula de cada vez, com o botão ▶ à esquerda ou `Shift + Enter`. Espere cada uma terminar antes de seguir.

### Célula 1: confirmar a GPU

Resultado esperado:

```text
CUDA disponível: True
GPU: Tesla T4
```

Se aparecer `False`, volte à Parte 4.

### Célula 2: montar o Drive e extrair o projeto

O Google pede autorização para acessar o Drive. Aceite com a mesma conta onde está o ZIP.

Resultado esperado: `Projeto extraído de /content/drive/MyDrive/trabalho-llm.zip`, seguido da lista de arquivos com `requirements.txt`.

O projeto fica em `Meu Drive/trabalho-llm/`. Os resultados do treino também são gravados lá.

### Célula 3: instalar dependências

Usa `requirements-colab.txt`, que mantém o PyTorch já instalado no Colab. O `requirements.txt` não serve no Colab: ele fixa versões para Python 3.12, e o `sentencepiece==0.2.0` falha ao compilar em Python mais novo.

A última linha deve mostrar algo como `torch 2.x | CUDA True | transformers 4.46.3 | bitsandbytes 0.x`.

Leva alguns minutos. Avisos em vermelho sobre conflitos de versão de outros pacotes do Colab são comuns e podem ser ignorados se a célula terminar.

Se o Colab mostrar **Reiniciar sessão**, clique, execute de novo a **Célula 2** e siga para a **Célula 4** (não reinstale).

### Célula 4: gerar o dataset e rodar os testes

Resultado esperado no final:

```text
Validação concluída sem erros.
30 passed
```

Se algum teste falhar, pare e verifique se o ZIP enviado é o mais recente.

### Célula 5: treinar

Treina duas configurações (r=8 e depois r=16), como pede o PRD.

No início do log deve aparecer:

```text
INFO Modo de treino: qlora | r=8 | lr=0.0002
```

Se aparecer `Modo de treino: cpu`, a GPU não está ativa: interrompa e volte à Parte 4.

Ao final, a célula mostra a tabela `hparams.md` com o tempo e o menor `eval_loss` de cada configuração.

Não feche a aba durante o treino. Se a sessão cair, veja "Problemas comuns".

### Célula 6: ver as curvas de perda

Mostra `loss_r8.png` e `loss_r16.png`. A curva de validação (`eval_loss`) deve cair. Se ela subir no final enquanto a de treino continua caindo, houve overfitting: registre isso no relatório.

### Célula 7: avaliação cega Base vs Fine-Tuned

Roda os 30 exemplos de teste nos dois sistemas, sem revelar qual é qual até o final. Depois mostra a tabela de comparação.

Critério de sucesso do PRD:

- Valid JSON com limpeza ≥ 95%;
- Micro-F1 do Fine-Tuned maior que o do Base.

### Célula 8: teste com a planilha CSV

Avalia `data/samples/planilha_teste.csv` (8 linhas fictícias com gabarito) nos dois sistemas. Os resultados ficam em `outputs/eval/csv_planilha_teste_base.json` e `csv_planilha_teste_fine-tuned.json`.

### Célula 9: baixar os resultados

Gera e baixa `fine_tuned_outputs.zip`, com:

```text
outputs/adapter/   (adaptador final, sem checkpoints intermediários)
outputs/curves/    (curvas e hparams.md)
outputs/eval/      (métricas, comparação, gráfico, avaliação do CSV)
REPORT.md
```

Se o download não começar, abra o painel de arquivos (ícone de pasta, à esquerda) e baixe `fine_tuned_outputs.zip` manualmente. Uma cópia também fica em `Meu Drive/trabalho-llm/`.

---

## Parte 6: trazer os resultados para o computador da apresentação

No PowerShell, dentro da pasta do projeto:

```powershell
Expand-Archive -Path "$HOME\Downloads\fine_tuned_outputs.zip" -DestinationPath . -Force
```

Confirme:

```powershell
Test-Path .\outputs\adapter\adapter_config.json
```

Deve mostrar `True`. O `REPORT.md` local é substituído pelo gerado no Colab.

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Opcional: repetir o teste do CSV no computador local com o Fine-Tuned (na CPU leva alguns minutos):

```powershell
python src/eval/evaluate_csv.py --csv data/samples/planilha_teste.csv --adapter outputs\adapter
```

Abra o app:

```powershell
streamlit run app/streamlit_app.py
```

Com o adaptador presente, o app já abre com **Fine-Tuned** selecionado na barra lateral. Na CPU, cada documento leva de 10 a 25 segundos.

---

## Parte 7: se mudar o código depois

1. Gere o ZIP de novo (Parte 1).
2. No Drive, apague o `trabalho-llm.zip` antigo e envie o novo (Parte 2).
3. No Colab, execute a Célula 2 novamente: ela atualiza o código sem apagar `outputs/`.

---

## Problemas comuns

### `CUDA disponível: False` ou `Modo de treino: cpu`

A GPU não está ativa. Repita a Parte 4. Se não houver GPU disponível no Colab gratuito, tente em outro horário.

### `Projeto não encontrado` ou `requirements.txt não encontrado` na Célula 2

Causas possíveis:

- o ZIP não está na raiz do Meu Drive ou tem outro nome (por exemplo, `trabalho-llm (1).zip`). Renomeie para `trabalho-llm.zip` e deixe-o fora de qualquer pasta;
- o ZIP foi criado de outra forma (botão direito > Compactar, ou `tar` executado fora da pasta do projeto) e tem uma pasta interna. A versão atual da Célula 2 encontra o projeto mesmo assim e mostra `Pasta do projeto: ...`.

Para ver o que foi extraído:

```python
!find /content/drive/MyDrive/trabalho-llm -maxdepth 3 -name requirements.txt -not -path "*/.venv/*"
```

### A sessão caiu no meio do treino

Reconecte, execute as Células 1, 2 e 3 e depois a Célula 5 de novo. O treino recomeça do zero, mas o que já foi gravado em `Meu Drive/trabalho-llm/outputs/` não se perde.

### `Failed building wheel for sentencepiece` na Célula 3

Acontece quando a Célula 3 instala `requirements.txt` em vez de `requirements-colab.txt` (notebook antigo). Troque a linha de instalação por:

```python
!pip install -q -r requirements-colab.txt
```

Se o arquivo `requirements-colab.txt` não existir no Drive, o ZIP enviado é antigo: use a alternativa abaixo, que tem o mesmo efeito.

```python
!grep -vE "^(torch|sentencepiece|bitsandbytes)==" requirements.txt > /tmp/req.txt
!pip install -q -r /tmp/req.txt "sentencepiece>=0.2.1" "bitsandbytes>=0.45"
```

### `CUDA out of memory`

Reduza `batch_size` para `1` e aumente `gradient_accumulation` para `8` em `configs/train.yaml`, gere o ZIP de novo e repita a Parte 7.

### O Fine-Tuned não superou o Base

Não altere o conjunto de teste nem o gabarito. Registre os números reais no `REPORT.md` e analise os erros em `outputs/eval/comparison.md`.

---

## Checklist final

- [ ] `trabalho-llm.zip` gerado sem `.venv`, `.git`, `outputs` e `.env`;
- [ ] ZIP na raiz do Meu Drive;
- [ ] Célula 1 mostrou `CUDA disponível: True`;
- [ ] Célula 4 mostrou `30 passed`;
- [ ] Célula 5 mostrou `Modo de treino: qlora`;
- [ ] `fine_tuned_outputs.zip` baixado e extraído na pasta do projeto;
- [ ] `outputs/adapter/adapter_config.json` existe;
- [ ] métricas reais registradas no `REPORT.md`.
