# Dockerfile

# Stage 1: Imagem base para o ambiente de execução Python
FROM python:3.11-slim-buster

# Define variáveis de ambiente
ENV PYTHONUNBUFFERED 1
ENV APP_PORT 8080

# Cria o diretório de trabalho na imagem
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte
# A ordem é importante: primeiro as dependências para aproveitar o cache do Docker
COPY src/ /app/src/

# Comando de execução. 
# Ele inicia o servidor Uvicorn rodando a aplicação 'app' do módulo 'main'.
# O host 0.0.0.0 garante que o serviço será acessível de fora do contêiner.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]