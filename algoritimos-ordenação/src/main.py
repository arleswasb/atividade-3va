# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from .communication import send_acks_to_all_peers
import uvicorn
import os
import asyncio
import httpx
import uuid


# Importações dos módulos de lógica e modelos
from .process_logic import (
    PROCESS_ID, LOGICAL_CLOCK, PEERS, 
    update_clock, receive_and_enqueue_message, receive_ack
)
from .models import Message

app = FastAPI(title=f"Processo P{PROCESS_ID} - Multicast")
PORT = 8080 
PEER_PORT = 8080 # Porta padrão para comunicação entre Pods

# Endpoint base para obter o status
@app.get("/")
def read_root():
    """Retorna o estado atual do processo."""
    return {
        "process_id": PROCESS_ID, 
        "current_clock": LOGICAL_CLOCK, 
        "status": "Running",
        "peers": PEERS
    }

# --- ENDPOINTS DE RECEBIMENTO ---

@app.post("/message")
async def receive_message_endpoint(message: Message):
    """Recebe uma nova mensagem de multicast de um par."""
    print(f"Recebido MENSAGEM de P{message.sender_id} (TS: {message.timestamp})")
    # A chamada deve ser AWAIT
    await receive_and_enqueue_message(message)
    return {"status": "Message received and enqueued."}

@app.post("/ack")
async def receive_ack_endpoint(ack_data: dict):
    """Recebe um ACK de um processo para uma mensagem."""
    message_id = ack_data.get("message_id")
    if not message_id:
        raise HTTPException(status_code=400, detail="message_id is required")

    # Simula um atraso de ACK para testar o Cenário 2 da AV2
    if message_id == os.environ.get("DELAY_MSG_ID", "") and PROCESS_ID == int(os.environ.get("DELAY_PROC_ID", -1)):
        print(f"[{LOGICAL_CLOCK}] --- SIMULANDO ATRASO de ACK para {message_id} (P{PROCESS_ID}) ---")
        await asyncio.sleep(5) # Atraso de 5 segundos

    print(f"Recebido ACK para mensagem {message_id}")
    receive_ack(message_id)
    return {"status": "ACK processed."}

# --- ENDPOINT DE ENVIO (START) ---

@app.post("/send")
async def send_multicast_message(content: str):
    """Endpoint que um cliente externo chama para disparar o envio de uma mensagem."""
    
    # 1. Preparar a Mensagem
    message_id = str(uuid.uuid4())
    new_timestamp = update_clock() # Incrementa e obtém o novo TS
    
    new_message = Message(
        sender_id=PROCESS_ID,
        message_id=message_id,
        timestamp=new_timestamp,
        content=content
    )
    
    # 2. Enviar a mensagem para todos os pares (EXCETO a si mesmo)
    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = []
        for peer_id in range(len(PEERS)):
            peer_host = f"{PEERS[peer_id]}" 
            
            if peer_id == PROCESS_ID:
                continue 

            # Constrói o FQDN (Fully Qualified Domain Name) para o Pod
            peer_host = f"{PEERS[peer_id]}.algoritmos-svc"
            url = f"http://{peer_host}:{PEER_PORT}/message"
            print(f"P{PROCESS_ID} enviando MENSAGEM {message_id} para {peer_host}...")
            
            tasks.append(client.post(url, json=new_message.dict()))
            
        # Esperar que todas as chamadas de envio terminem
        await asyncio.gather(*tasks, return_exceptions=True)

    # 3. O remetente também deve processar a sua própria mensagem (e disparar seus ACKs)
    # A chamada deve ser AWAIT
    await receive_and_enqueue_message(new_message) 
    
    # NOTA: receive_and_enqueue_message irá enviar o ACK do remetente para todos, e
    # os outros processos receberão a mensagem e enviarão seus ACKs de volta.
    # O ciclo está fechado.

    return JSONResponse(
        content={"status": "Multicast initiated successfully.", "message_id": message_id, "timestamp": new_timestamp},
        status_code=200
    )

# Função principal de inicialização
if __name__ == "__main__":
    # O nome do POD é a forma mais robusta de obter o ID em K8s
    print(f"Iniciando Processo P{PROCESS_ID} com Relógio Inicial: {LOGICAL_CLOCK}")
    # O host '0.0.0.0' é necessário para expor o servidor dentro do contêiner
    uvicorn.run(app, host="0.0.0.0", port=PORT)