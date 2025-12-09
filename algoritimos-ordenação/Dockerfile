# Define a imagem base
FROM python:3.9-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de dependências
COPY requirements.txt .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Cria o diretório de logs
RUN mkdir -p /app/logs

# Copia o código da aplicação (mantendo a estrutura do pacote src)
COPY ./src ./src

# Expõe a porta que a aplicação vai rodar
EXPOSE 8080

# Comando para iniciar a aplicação (aponta para src.main)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]