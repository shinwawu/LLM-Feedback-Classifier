# Usa uma versão leve do Python
FROM python:3.10-slim

# Instala o gestor de pacotes 'uv' diretamente da fonte oficial
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Define o diretório de trabalho dentro do contentor
WORKDIR /app

# Copia os ficheiros de dependência primeiro (para otimizar o cache do Docker)
COPY pyproject.toml ./

# Instala as dependências usando o uv no ambiente global do contentor
RUN uv pip install --system -r pyproject.toml

# Copia todo o resto do projeto para dentro do contentor
COPY . .

# (Não definimos o CMD aqui porque o docker-compose vai decidir se roda a API ou o Front)