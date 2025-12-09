# src/logger.py
import sys
import os
from loguru import logger

# Remove o handler padrão para garantir que apenas nossa configuração seja usada
logger.remove()

# Define o formato simplificado do log, focando na hora, nível, processo e mensagem.
log_format = (
    "<green>{time:HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[process_name]: <12}</cyan> | "
    "<level>{message}</level>"
)

# Adiciona um novo handler para o console com o formato simplificado
logger.add(
    sys.stderr,
    format=log_format,
    level="INFO",
    colorize=True
)

# Função para adicionar dinamicamente o nome do processo aos logs
def patch_logger_with_process_name():
    try:
        # Extrai o ID do processo do nome do Pod (ex: 'algoritmos-coord-0' -> 0)
        process_id = int(os.environ.get('POD_NAME').split('-')[-1])
        process_name = f"Processo-{process_id}"
    except (ValueError, AttributeError):
        # Fallback para quando não estamos rodando em K8s
        process_name = "Teste-Local"
        
    # Configura o logger para incluir o 'process_name' em todos os registros
    logger.configure(extra={"process_name": process_name})

# Aplica a configuração assim que o módulo é importado
patch_logger_with_process_name()

# Exporta o logger configurado para ser usado em outros módulos
__all__ = ["logger"]
