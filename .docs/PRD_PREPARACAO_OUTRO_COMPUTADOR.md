# PRD — Preparar outro computador para apresentar o projeto

## 1. Objetivo

Permitir que uma pessoa da equipe clone o repositório do GitHub em outro computador, instale as dependências adequadas e execute os testes e o painel Streamlit para a apresentação.

## 2. Resultado esperado

No computador preparado, a pessoa deve conseguir:

1. instalar as bibliotecas do projeto;
2. executar os testes automatizados;
3. validar os dados;
4. abrir o painel Streamlit;
5. testar um documento de exemplo;
6. baixar o resultado em CSV.

## 3. Requisitos do computador

- Conexão com a internet para clonar o repositório e baixar o modelo na primeira execução.
- Git instalado.
- Python 3.12 instalado.
- Espaço livre para instalar PyTorch, bibliotecas e os arquivos do modelo.
- Para executar o painel com o modelo Base, não é obrigatória uma GPU, mas a execução em CPU pode ser lenta.
- Para treinar o modelo com QLoRA, é necessária uma GPU NVIDIA compatível com CUDA. O Google Colab é uma alternativa.

## 4. Arquivos relacionados

- `requirements-presentation.txt`: dependências para testes, painel e apresentação; não inclui `bitsandbytes`.
- `requirements.txt`: dependências completas, incluindo `bitsandbytes`, para ambientes de treinamento compatíveis.
- `configs/train.yaml`: parâmetros de treino.
- `data/samples/`: documentos pequenos para demonstração.
- `outputs/adapter/`: adaptador do modelo Fine-Tuned, criado após o treino e não incluído no repositório por padrão.

## 5. Preparação no Windows

### 5.1 Clonar o repositório

Substitua `<URL_DO_REPOSITORIO>` pelo endereço HTTPS do repositório no GitHub:

```powershell
git clone <URL_DO_REPOSITORIO>
cd trabalho-llm
```

### 5.2 Criar o ambiente e instalar as dependências

Execute os comandos dentro da pasta clonada:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-presentation.txt
```

Se a ativação do ambiente for bloqueada pelo PowerShell, execute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### 5.3 Verificar a instalação

```powershell
python -m pip check
python -m pytest -q
python src/data/validate_dataset.py
```

Critérios esperados:

- `pip check` informa que não há dependências quebradas;
- os testes terminam com `passed`;
- o validador termina com `Validação concluída sem erros.`

### 5.4 Abrir o painel

```powershell
streamlit run app/streamlit_app.py
```

No navegador:

1. selecione o exemplo `relatorio.txt`;
2. escolha `Base` se ainda não houver adaptador treinado;
3. clique em `Extrair entidades`;
4. confira a tabela e o JSON bruto;
5. clique em `Baixar CSV`.

## 6. Preparação em Linux ou macOS

Instale Git e Python 3.12. Em seguida:

```bash
git clone <URL_DO_REPOSITORIO>
cd trabalho-llm
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-presentation.txt
python -m pip check
python -m pytest -q
python src/data/validate_dataset.py
streamlit run app/streamlit_app.py
```

## 7. Modelo Base e Fine-Tuned

- **Base:** pode ser escolhido no painel sem adaptador treinado. Na primeira inferência, o Transformers baixa os arquivos do modelo pela internet.
- **Fine-Tuned:** precisa da pasta `outputs/adapter/` criada pelo treinamento. Essa pasta contém os pesos do adaptador e não é criada apenas ao clonar o código.
- Para demonstrar Fine-Tuned em outra máquina, copie a pasta `outputs/adapter/` para o mesmo caminho no projeto clonado ou publique os pesos separadamente. Não invente resultados se o adaptador ou as métricas não estiverem disponíveis.
- Para treinamento QLoRA, instale `requirements.txt` somente em um ambiente compatível com CUDA. Em Windows sem suporte adequado a `bitsandbytes`, use o Colab ou Linux com GPU.

## 8. Arquivos que devem estar no GitHub

O repositório deve incluir o código-fonte, documentação, configurações, testes, exemplos pequenos e os arquivos JSONL processados necessários para validar o dataset.

Não é necessário enviar:

- `.venv/`;
- `.pytest_cache/`;
- arquivos temporários;
- segredos ou chaves de API;
- pesos grandes do modelo base;
- adaptador Fine-Tuned, a menos que a equipe decida conscientemente distribuí-lo via Git LFS ou outro armazenamento.

Depois de clonar, os dados podem ser regenerados com:

```powershell
python src/data/generate_dataset.py --seed 42 --output data/raw/dataset.jsonl
python src/data/split_dataset.py --input data/raw/dataset.jsonl --output-dir data/processed --seed 42
python src/data/validate_dataset.py
```

## 9. Critérios de aceite

- O repositório clona sem precisar de caminhos locais absolutos.
- As instruções funcionam com uma instalação limpa do Python 3.12.
- Testes e validação de dados passam.
- O Streamlit inicia e permite demonstrar um exemplo usando Base.
- A documentação deixa explícito que Fine-Tuned exige o adaptador já treinado.
