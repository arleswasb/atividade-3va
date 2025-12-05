# src/models.py

from pydantic import BaseModel
from typing import Optional

class Message(BaseModel):
    """Estrutura da mensagem para o Multicast."""
    sender_id: int
    message_id: str
    timestamp: int
    content: str
    # Opcional para o ACK, mas é útil para tipagem
    delay_ms: Optional[int] = 0