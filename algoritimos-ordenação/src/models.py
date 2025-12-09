# src/models.py
from pydantic import BaseModel
from typing import List

class Message(BaseModel):
    """
    Representa uma mensagem de multicast com todos os seus metadados.
    """
    sender_id: int
    message_id: str
    timestamp: int
    content: str

class Ack(BaseModel):
    """
    Representa uma mensagem de confirmação (ACK).
    """
    message_id: str
    process_id: int

class SCRequest(BaseModel):
    """Mensagem de Requisição de Seção Crítica (SC)."""
    request_ts: int
    process_id: int