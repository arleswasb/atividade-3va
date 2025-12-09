# src/main.py (VERSÃO FINAL)
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
import os
import uuid
from typing import Set

# Importações centralizadas
from src.logger import logger
from src.config import PROCESS_ID, PEERS, PEER_PORT
from src.models import Message, Ack, SCRequest
from src.process_logic import LOGICAL_CLOCK

app = FastAPI(title=f"Processo P{PROCESS_ID} - Algoritmos Distribuídos")

# --- Gerenciamento de Tarefas em Background ---
# Manter uma referência forte às tarefas para evitar que sejam coletadas pelo garbage collector
background_tasks: Set[asyncio.Task] = set()


def create_background_task(coroutine):
    """Cria e gerencia uma tarefa em background."""
    logger.info(f"Agendando a corrotina '{coroutine.__name__}' para execução em background.")
    task = asyncio.create_task(coroutine)
    background_tasks.add(task)
    # Adiciona um callback para remover a tarefa do conjunto quando ela terminar
    task.add_done_callback(background_tasks.discard)


# --- Endpoints da API ---

@app.get("/")
def read_root():
    """Endpoint de status para verificar a saúde e o estado atual do processo."""
    return {"process_id": PROCESS_ID, "current_clock": LOGICAL_CLOCK, "status": "Running"}

# --- Endpoints para Exclusão Mútua (Q2) ---

@app.post("/request-resource", status_code=202)
async def request_resource_endpoint():
    """Inicia o pedido de acesso à região crítica."""
    from .process_logic import request_resource_access
    logger.info("Endpoint /request-resource chamado.")
    create_background_task(request_resource_access())
    return {"status": "Resource request initiated. Processing in background."}

@app.post("/receive-request", status_code=202)
async def receive_request_endpoint(request: SCRequest):
    """Recebe um pedido de recurso de outro processo."""
    from .process_logic import handle_resource_request
    logger.info(f"Recebido REQUEST de P{request.process_id} com TS={request.request_ts}.")
    create_background_task(handle_resource_request(request.request_ts, request.process_id))
    return {"status": "Request received. Processing in background."}

@app.post("/receive-reply", status_code=202)
async def receive_reply_endpoint(sender_id: int):
    """Recebe uma resposta (REPLY) de outro processo."""
    from .process_logic import handle_reply
    logger.info(f"Recebido REPLY de P{sender_id}.")
    create_background_task(handle_reply())
    return {"status": "Reply received. Processing in background."}

# --- Endpoints para Eleição de Líder (Q3) ---

@app.post("/start-election", status_code=202)
async def start_election_endpoint():
    """Inicia uma eleição de líder."""
    from .process_logic import start_election
    logger.info("Endpoint /start-election chamado. Iniciando eleição...")
    create_background_task(start_election())
    return {"status": "Election started. Processing in background."}

@app.post("/receive-election", status_code=202)
async def receive_election_endpoint(candidate_id: int):
    """Recebe uma mensagem de ELECTION de outro processo."""
    from .process_logic import handle_election_message
    logger.info(f"Recebido ELECTION de P{candidate_id}.")
    create_background_task(handle_election_message(candidate_id))
    return {"status": "Election message received. Processing in background."}

@app.post("/receive-answer", status_code=202)
async def receive_answer_endpoint(peer_id: int):
    """Recebe uma mensagem de ANSWER durante uma eleição."""
    from .process_logic import handle_answer_message
    logger.info(f"Recebido ANSWER de P{peer_id}.")
    create_background_task(handle_answer_message(peer_id))
    return {"status": "Answer message received. Processing in background."}

@app.post("/receive-coordinator", status_code=202)
async def receive_coordinator_endpoint(leader_id: int):
    """Recebe notificação de um novo líder."""
    from .process_logic import handle_coordinator_message
    logger.info(f"Recebido COORDINATOR notificando P{leader_id} como novo líder.")
    create_background_task(handle_coordinator_message(leader_id))
    return {"status": "Coordinator message received. Processing in background."}

# --- Endpoints da API para Multicast (Q1) - Mantidos para compatibilidade ---

@app.post("/message")
async def receive_message_endpoint(message: Message):
    from .process_logic import receive_and_enqueue_message
    logger.info(f"Recebido MENSAGEM de P{message.sender_id} (TS: {message.timestamp})")
    create_background_task(receive_and_enqueue_message(message))
    return {"status": "Message received and enqueued."}

@app.post("/ack")
async def receive_ack_endpoint(ack: Ack):
    from .process_logic import receive_ack
    logger.info(f"Recebido ACK para mensagem {ack.message_id}")
    receive_ack(ack.message_id)
    return {"status": "ACK processed."}

@app.post("/send")
async def send_multicast_message(content: str):
    from .communication import send_message_to_peers
    from .process_logic import update_clock, receive_and_enqueue_message

    # Lógica para acionar o atraso de teste
    is_delayed_message = "com atraso" in content.lower()
    msg_id = "MSG_PARA_ATRASAR" if is_delayed_message else str(uuid.uuid4())

    new_timestamp = update_clock()
    new_message = Message(
        sender_id=PROCESS_ID,
        message_id=msg_id,
        timestamp=new_timestamp,
        content=content
    )
    
    log_msg = f"Iniciando multicast da mensagem {new_message.message_id}"
    if is_delayed_message:
        log_msg += " (com gatilho de atraso)"
    logger.info(log_msg)

    create_background_task(send_message_to_peers(new_message))
    create_background_task(receive_and_enqueue_message(new_message))
    
    return JSONResponse(
        content={"status": "Multicast initiated.", "message_id": new_message.message_id},
        status_code=200
    )
# --- Função para iniciar o servidor ---

def start():
    """Inicia o servidor uvicorn."""
    logger.info(f"--- VERSÃO FINAL --- Iniciando processo P{PROCESS_ID} na porta {PEER_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PEER_PORT)

if __name__ == "__main__":
    start()