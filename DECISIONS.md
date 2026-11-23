# DECISÕES

- **Linguagem e estilo:** Python 3.10+ com módulos pequenos, nomes claros e type hints nas interfaces públicas.
- **Dataset:** com 200 amostras sintéticas e semente fixa 42. A divisão final é estratificada por categoria em 140/30/30.
- **Datas sem ano:** o ano padrão é 2026.
- **Gabarito:** todos os registros sintéticos são gerados pelo código; a API opcional não é usada para criar rótulos.
- **Inferência:** backend local por padrão e backend HTTP opcional pelo serviço OpenAI-compatible.
- **Treino:** o script usa o stack Transformers + PEFT + bitsandbytes como implementação direta e mantém os parâmetros em YAML.
- **Ambiguidade de IP em texto sem entidade:** exemplos marcados como não relacionados são excluídos pelo gabarito.
