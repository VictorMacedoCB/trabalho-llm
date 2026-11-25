# Visão geral do projeto para apresentação

## 1. Resumo em uma frase

Este projeto recebe documentos técnicos ruidosos, usa uma LLM ajustada com QLoRA para encontrar evidências digitais e transforma o resultado em uma tabela JSON/CSV.

Entidades procuradas:

- data;
- endereço IPv4;
- usuário;
- nome de arquivo;
- hash.

Exemplo simplificado:

```text
Entrada:
"No dia 14/03, o IP 192.168.1.45 foi usado pelo admin às 10:15,
baixando backup.zip com hash 4a8f..."

Saída:
[{"data":"2026-03-14 10:15","ip":"192.168.1.45","usuario":"admin","arquivo":"backup.zip","hash":null}]
```

O campo `hash` é `null` no exemplo acima porque `4a8f...` está truncado e o projeto só aceita hash completo.

## 2. Objetivo do projeto

O objetivo é comparar dois sistemas:

1. **Modelo Base:** modelo Qwen original, sem treinamento adicional.
2. **Modelo Fine-Tuned:** o mesmo modelo após receber um adaptador de treino QLoRA.

O projeto deve avaliar qual dos dois segue melhor três requisitos:

- devolver JSON válido;
- encontrar as entidades corretas;
- evitar inventar informações.

O resultado deve ser exibido em uma interface simples feita com Streamlit.

## 3. Modelo utilizado

### Modelo Base

O modelo configurado é:

```text
Qwen/Qwen2.5-1.5B-Instruct
```

Significado das partes:

- **Qwen:** família de modelos da Alibaba;
- **2.5:** versão da família;
- **1.5B:** aproximadamente 1,5 bilhão de parâmetros;
- **Instruct:** modelo preparado para seguir instruções.

É considerado pequeno para uma LLM, mas ainda precisa de bastante memória e processamento. Na configuração, ele pode ser substituído por outros modelos compatíveis em `configs/train.yaml`.

### Fine-Tuned

Fine-tuning significa ajustar o modelo usando exemplos próprios.

QLoRA significa que o modelo é carregado em 4 bits e recebe pequenos ajustes chamados LoRA. Isso permite treinar um modelo grande sem salvar uma cópia completa dele.

No projeto:

- quantização: 4-bit NF4;
- quantização dupla;
- LoRA `r=16`;
- LoRA `alpha=32`;
- dropout `0.05`;
- camadas ajustadas: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj` e `down_proj`.

O modelo não deve ser explicado como “aprendeu dados pessoais”; ele aprende o padrão de entrada, saída e formato JSON.

## 4. Stack tecnológica

| Tecnologia | Função |
|---|---|
| Python 3.10+ | Linguagem principal |
| Python 3.12 | Versão recomendada para preparação |
| PyTorch | Execução e treino de redes neurais |
| Transformers | Carregar o modelo, tokenizar texto e gerar resposta |
| PEFT | Criar e carregar os adaptadores LoRA |
| bitsandbytes | Quantização 4-bit durante o treino |
| TRL | Treinador para ajuste do modelo |
| Datasets | Leitura e processamento dos arquivos JSONL |
| PyYAML | Ler o arquivo `configs/train.yaml` |
| Streamlit | Interface web de demonstração |
| pandas | Transformar entidades em tabela |
| pypdf | Ler texto de arquivos PDF |
| matplotlib | Criar gráficos de treino e avaliação |
| pytest | Executar testes automáticos |

Para a apresentação e demonstração, existe `requirements-presentation.txt`, que não inclui `bitsandbytes`.

## 5. Como o projeto funciona

Fluxo geral:

```text
Documento do usuário
        ↓
Divisão em partes de até aproximadamente 1500 caracteres
        ↓
SYSTEM_PROMPT com as regras de extração
        ↓
Modelo Base ou Fine-Tuned
        ↓
Resposta JSON
        ↓
Validação de schema, IP, hash e data
        ↓
Tabela do Streamlit
        ↓
Exportação para CSV
```

O sistema não procura simplesmente palavras-chave. Ele envia o documento e as regras para uma LLM, que tenta compreender o contexto e produzir uma estrutura JSON.

Depois da resposta, o projeto valida o formato usando funções Python. Isso reduz inconsistências, mas não corrige todas as respostas erradas do modelo.

## 6. Contrato de saída

A resposta deve ser uma lista JSON.

Cada objeto deve conter exatamente:

```json
{
  "data": null,
  "ip": null,
  "usuario": null,
  "arquivo": null,
  "hash": null
}
```

Regras importantes:

- todos os cinco campos são obrigatórios;
- campo ausente recebe `null`;
- texto sem entidades retorna `[]`;
- um texto com dois eventos retorna dois objetos;
- o projeto não deve inventar valores;
- IP com defang como `192[.]168[.]1[.]45` vira `192.168.1.45`;
- datas sem ano usam 2026;
- hash completo aceita apenas 32, 40 ou 64 caracteres hexadecimais;
- usuários são escritos em minúsculas quando são logins;
- arquivos devem possuir extensão.

## 7. Dataset

### Volume

O dataset sintético possui 200 amostras:

- 140 para treino;
- 30 para validação;
- 30 para teste.

Os arquivos estão em:

- `data/processed/train.jsonl`;
- `data/processed/val.jsonl`;
- `data/processed/test.jsonl`.

### Por que sintético?

Os exemplos são gerados por templates em Python. Isso permite controlar exatamente quais entidades existem em cada texto e garante um gabarito correto.

A geração usa a semente fixa `42`, portanto pode ser reproduzida.

O gerador não depende de uma API de LLM. Uma API externa é opcional para diversificar textos, mas não é usada para criar o gabarito.

### Categorias

| Categoria | Quantidade aproximada | Finalidade |
|---|---:|---|
| Um evento | 35% | Um documento com várias informações |
| Múltiplos eventos | 30% | Dois ou três eventos no mesmo texto |
| Ruído pesado | 15% | Erros, quebras e informações irrelevantes |
| Campos parciais | 10% | Alguns campos ausentes |
| Sem entidade | 10% | Texto sem evidências |

Os modelos de documento incluem:

- relatório técnico;
- transcrição ASR;
- log de auditoria;
- e-mail de incidente.

### Formato ChatML

Cada linha usa mensagens:

```text
system  = instruções gerais
user    = texto do documento
assistant = lista JSON esperada
meta    = categoria e tipo do exemplo
```

O campo `meta` é usado para análise e divisão, mas não entra na resposta ensinada ao modelo.

## 8. Higienização e validação

O script `src/data/validate_dataset.py` verifica:

- JSON do assistant parseável;
- campos conforme o schema;
- IP válido entre 0 e 255 em cada octeto;
- hash com 32, 40 ou 64 caracteres;
- valores presentes no texto;
- duplicatas exatas;
- quase duplicatas acima de Jaccard 0,85;
- vazamento entre treino, validação e teste;
- quantidade de categorias.

O vazamento é importante: nenhum IP, hash ou nome de arquivo usado no treino pode reaparecer nos conjuntos de validação ou teste.

## 9. Estrutura das pastas

### `.docs/`

Contém a documentação do projeto:

- PRD original;
- PRD para preparar outro computador;
- guia de apresentação;
- visão geral atual.

### `app/`

Contém a interface Streamlit.

Arquivo principal:

- `app/streamlit_app.py`.

Responsabilidades:

- upload de arquivo;
- entrada de texto;
- seleção de exemplo;
- seleção Base/Fine-Tuned;
- divisão do texto;
- tabela de evidências;
- contadores;
- download CSV;
- JSON bruto.

### `configs/`

Contém [configs/train.yaml](../configs/train.yaml), que guarda os parâmetros do treino.

Exemplos:

- modelo;
- semente;
- número de épocas;
- taxa de aprendizado;
- tamanho dos lotes;
- LoRA;
- sequência máxima.

Separar parâmetros em YAML permite alterar o experimento sem editar o código.

### `data/`

#### `data/raw/`

Saída bruta da geração sintética.

#### `data/processed/`

Arquivos utilizados no treino e avaliação:

- `train.jsonl`;
- `val.jsonl`;
- `test.jsonl`.

#### `data/samples/`

Três documentos pequenos para demonstrar o aplicativo.

### `src/common.py`

É o núcleo das regras compartilhadas:

- `SYSTEM_PROMPT`;
- nomes dos campos;
- validação de IP;
- validação de hash;
- normalização de data;
- remover defang;
- analisar JSON;
- validar schema.

O mesmo prompt é usado pelo dataset, treino, avaliação e aplicativo.

### `src/data/`

Scripts de preparação dos dados:

- `generate_dataset.py`: cria os exemplos;
- `split_dataset.py`: divide em treino, validação e teste;
- `validate_dataset.py`: verifica qualidade e vazamento.

### `src/train/`

Contém `train_qlora.py`.

Esse script:

- lê o YAML;
- fixa a semente;
- baixa o modelo;
- carrega em 4 bits;
- cria o adaptador LoRA;
- treina;
- salva o adaptador;
- salva o histórico e o gráfico de perda.

### `src/inference.py`

É a única interface usada pela avaliação e pelo aplicativo.

Pode trabalhar em dois modos:

- `local`: executa o modelo no computador;
- `http`: envia o texto para um servidor compatível com OpenAI.

A seleção usa as variáveis de ambiente:

- `BACKEND`;
- `INFERENCE_URL`;
- `MODEL_NAME`.

### `src/eval/`

#### `metrics.py`

Calcula todas as métricas.

#### `run_inference.py`

Executa o Base e o Fine-Tuned no conjunto de teste e grava resultados com nomes cegos.

#### `compare.py`

Lê o arquivo `.key.json`, revela qual sistema era qual e gera os relatórios e gráficos.

### `notebooks/`

Contém `train_colab.ipynb`, usado para executar o treino em uma máquina com GPU, como o Google Colab.

### `outputs/`

Resultados gerados:

- `outputs/adapter/`: adaptador LoRA;
- `outputs/curves/`: gráficos e histórico;
- `outputs/eval/`: resultados da avaliação.

### `tests/`

Testes automatizados de normalização, JSON, schema e métricas.

## 10. Como o treino funciona

### Hiperparâmetros principais

Do arquivo `configs/train.yaml`:

- modelo: Qwen 2.5 1.5B Instruct;
- semente: 42;
- tamanho máximo da sequência: 1024;
- taxa de aprendizado: 0,0002;
- scheduler: cosine;
- aquecimento: 5%;
- épocas: 3;
- batch por dispositivo: 2;
- acumulação: 4;
- weight decay: 0,01;
- avaliação a cada 10 passos;
- LoRA r: 16;
- LoRA alpha: 32.

### O que é batch?

É a quantidade de exemplos processados por vez.

### O que é acumulação de gradiente?

Permite simular lotes maiores sem exigir tanta memória. Com batch 2 e acumulação 4, o projeto usa uma atualização efetiva equivalente a 8 exemplos.

### O que é loss?

Loss é o erro do modelo durante o treinamento.

- `train_loss`: erro nos exemplos de treino;
- `eval_loss`: erro nos exemplos reservados para validação.

A perda de treino deve cair. Se a perda de validação aumentar, pode haver overfitting.

### O que é overfitting?

É quando o modelo memoriza os exemplos de treino e perde capacidade de resolver exemplos novos.

### Melhor checkpoint

O código tenta manter o melhor resultado pela menor `eval_loss` e salvar o adaptador em `outputs/adapter/`.

O projeto também pode executar uma comparação de `r=8` contra `r=16`.

## 11. Como a avaliação funciona

O conjunto de teste tem 30 exemplos.

Esses exemplos não foram usados no treino nem na escolha do melhor hiperparâmetro.

Cada texto passa pelos dois sistemas:

```text
Base sem adaptador
Fine-Tuned com adaptador
```

Antes da comparação, as predições recebem nomes aleatórios:

- `sistema_A`;
- `sistema_B`.

Somente `compare.py` revela qual é Base e qual é Fine-Tuned.

Essa técnica evita analisar os resultados de forma enviesada.

## 12. Métricas explicadas

### Valid JSON Raw

Porcentagem de respostas que já eram JSON válido sem qualquer limpeza.

### Valid JSON Clean

Porcentagem que vira JSON válido quando cercas simples como ` ```json ` são removidas.

### Schema Valid

Porcentagem das respostas JSON que possuem exatamente os cinco campos e tipos permitidos.

### Precision

Entre todas as entidades previstas, quantas estavam corretas.

### Recall

Entre todas as entidades que deveriam ser encontradas, quantas foram encontradas.

### F1

Combina Precision e Recall em uma única medida.

### Micro-F1

Calcula todas as entidades juntas.

### Macro-F1

Calcula o F1 de cada campo e tira a média dos cinco.

### Exact Match

Porcentagem dos documentos cuja lista completa foi exatamente igual ao gabarito.

### Taxa de alucinação

Porcentagem dos valores previstos que não aparecem no texto de entrada.

### Precision, Recall e F1 por entidade

São calculados separadamente para:

- data;
- IP;
- usuário;
- arquivo;
- hash.

## 13. Interface Streamlit

A interface permite:

- enviar `.txt`;
- enviar `.log`;
- enviar `.csv`;
- enviar `.pdf`;
- colar texto;
- usar três exemplos prontos;
- alternar Base/Fine-Tuned;
- dividir documentos longos;
- mostrar contadores;
- avisar sobre IP ou hash suspeito;
- mostrar o JSON bruto;
- baixar o resultado em CSV.

Arquivos maiores são divididos em partes de até aproximadamente 1500 caracteres, com pequena sobreposição para não cortar eventos entre as partes.

## 14. Dependências

Há dois conjuntos:

### Apresentação

```text
requirements-presentation.txt
```

Usado para testes e interface Streamlit.

### Treinamento

```text
requirements.txt
```

Inclui `bitsandbytes` e as dependências completas do treino.

Python recomendado:

- 3.12 no Windows;
- 3.10 a 3.12 em geral.

## 15. Situação atual do projeto

O que está implementado e validado:

- geração do dataset;
- 200 amostras;
- divisão 140/30/30;
- validação do dataset sem erros;
- funções de normalização;
- testes automatizados;
- interface Streamlit;
- scripts de treino;
- scripts de avaliação;
- documentação.

O que ainda não pode ser afirmado sem a execução:

- adaptação real concluída;
- peso em `outputs/adapter/`;
- comparação numérica Base versus Fine-Tuned;
- gráfico real de F1;
- resultado final de `REPORT.md`.

Neste ambiente houve uma validação de:

- 13 testes aprovados;
- dependências principais carregadas;
- PyTorch em versão CPU;
- ausência de CUDA disponível.

Portanto, o treino deve ser feito em GPU, preferencialmente no Colab ou em outra máquina compatível.

## 16. Critérios de aceite do PRD

Os critérios principais são:

1. dataset válido com 150 a 200 exemplos;
2. divisão proporcional;
3. treino concluído em T4;
4. adaptador salvo;
5. gráfico de loss salvo;
6. comparação de pelo menos duas configurações;
7. avaliação cega;
8. Fine-Tuned com:
   - Valid JSON Rate maior ou igual a 95%;
   - Micro-F1 maior que o Base;
9. Streamlit funcional;
10. testes aprovados.

Se o Fine-Tuned não atingir 95% ou não superar o Base, o relatório deve mostrar os erros sem alterar os resultados.

## 17. Demonstração sugerida

### Passo 1

Abra o terminal na pasta do projeto.

### Passo 2

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Passo 3

Inicie:

```powershell
streamlit run app/streamlit_app.py
```

### Passo 4

Selecione `relatorio.txt`.

### Passo 5

Mostre:

- entrada;
- saída JSON;
- tabela;
- contadores;
- botão CSV.

### Passo 6

Explique o modelo Base.

### Passo 7

Mude para Fine-Tuned, somente se o adaptador existir.

### Passo 8

Não apresente a comparação como concluída sem `outputs/eval/results.json`.

## 18. Roteiro curto para falar sem decorar muito

> Nosso projeto cria um sistema de extração forense baseado em uma LLM pequena. A entrada é um relatório, transcrição, log ou e-mail com possíveis erros e informações irrelevantes. O sistema envia o texto e um prompt único para o modelo Qwen 2.5 1.5B.

> Primeiro criamos um dataset sintético com 200 exemplos. O conjunto foi dividido em 140 exemplos para treino, 30 para validação e 30 para teste. Ajustamos o modelo com QLoRA, uma técnica que altera pequenos componentes do modelo em vez de treinar todos os bilhões de parâmetros.

> Depois comparamos o modelo original com o modelo ajustado usando o conjunto de teste. Medimos JSON válido, schema, Precision, Recall, F1, Exact Match e alucinação.

> Por fim, construímos uma interface Streamlit. A banca pode enviar um arquivo ou texto, selecionar o modelo, visualizar a tabela de evidências e baixar o CSV.

## 19. Perguntas mais prováveis

### O modelo “entende” o texto?

Ele gera uma resposta com base em padrões aprendidos. Não possui uma base de conhecimento forense própria.

### Por que JSON?

JSON é estruturado e fácil de converter em tabela ou CSV.

### Por que o projeto usa normalização?

Para transformar datas, IPs e hashes em formatos uniformes antes da validação e das métricas.

### O que é defang?

É um método usado em textos técnicos para evitar que um IP seja interpretado automaticamente como endereço ativo. Exemplo: `192[.]168[.]1[.]45`.

### O que é um hash?

É uma sequência curta ou longa usada para identificar conteúdo. Neste projeto, apenas MD5, SHA-1 e SHA-256 completos são aceitos.

### Por que o modelo precisa de prompt?

O prompt explica a tarefa e o formato obrigatório da resposta.

### Por que separar sistema_A e sistema_B?

Para que a análise não saiba qual sistema é o Base e qual é o Fine-Tuned durante a primeira etapa.

### Por que não usar OCR?

O projeto não trata imagens ou leitura de imagens. PDF é tratado extraindo texto com `pypdf`.

### O que é LLMOps?

É o conjunto de práticas para preparar dados, testar, treinar, avaliar, versionar e publicar modelos de linguagem.

### O que significa 1.5B?

Aproximadamente 1,5 bilhões de parâmetros.

### O que significa LoRA?

São matrizes pequenas treináveis que modificam o comportamento do modelo sem atualizar todos os parâmetros.

### QLoRA melhora o modelo?

Não necessariamente. É necessário executar o treino e comparar o conjunto de teste para saber.

### O que pode ser apresentado como resultado?

Somente resultados reais gerados em `outputs/eval/results.json`, gráficos reais e análise escrita baseada nesses valores.

## 20. Limitações

- Dataset sintético pequeno;
- não cobre OCR;
- não usa autenticação;
- não possui banco de dados;
- não usa todos os formatos possíveis de idioma;
- CPU local é lenta;
- treinamento precisa de GPU;
- PDF depende de haver texto extraível;
- modelo pode errar JSON ou inventar entidades;
- normalização não substitui uma validação humana.
