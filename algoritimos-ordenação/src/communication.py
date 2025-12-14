# src/communication.py
import httpx
import asyncio
from src.config import PEERS, PEER_PORT, PROCESS_ID, TOTAL_PROCESSES
from src.logger import logger
from src.models import Message, Ack
from src.process_logic import LOGICAL_CLOCK
from src.models import SCRequest

# --- Funções de Comunicação para Multicast (Q1) ---

async def send_message_to_peers(message: Message):
    my_fqdn = f"algoritmos-coord-{PROCESS_ID}.algoritmos-coord-service" # FQDN do Pod atual
    logger.info(f"Enviando mensagem {message.message_id} para os pares.")
    async with httpx.AsyncClient() as client:
        for peer_name in PEERS:
            if peer_name == my_fqdn:
                continue
            
            url = f"http://{peer_name}:{PEER_PORT}/message"
            try:
                await client.post(url, json=message.dict(), timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar mensagem para {peer_name}: {e}")

async def send_acks_to_all_peers(message_id: str):
    """Envia confirmações (ACKs) para todos os processos, exceto a si mesmo."""
    logger.info(f"Enviando ACKs para a mensagem {message_id} para todos os pares (exceto self).")
    
    # Lógica de atraso para teste
    delay_msg_id = "MSG_PARA_ATRASAR"
    delay_proc_id = 2 # Processo 2 vai atrasar o ACK
    delay_seconds = 5

    if message_id == delay_msg_id and PROCESS_ID == delay_proc_id:
        logger.warning(f"ATRASO INDUZIDO: Atrasando ACK para msg {message_id} por {delay_seconds} segundos...")
        await asyncio.sleep(delay_seconds)

    # Não envie ACK para o próprio processo; o recebimento local já conta como 1 ACK
    my_fqdn = f"algoritmos-coord-{PROCESS_ID}.algoritmos-coord-service"
    ack_message = Ack(message_id=message_id, process_id=PROCESS_ID)
    async with httpx.AsyncClient() as client:
        for peer_name in PEERS:
            if peer_name == my_fqdn:
                continue
            url = f"http://{peer_name}:{PEER_PORT}/ack"
            try:
                await client.post(url, json=ack_message.dict(), timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar ACK para {peer_name}: {e}")


# --- NOVAS FUNÇÕES DE COMUNICAÇÃO PARA EXCLUSÃO MÚTUA (Q2) ---

async def send_request_to_peers(request_ts: int):
    my_fqdn = f"algoritmos-coord-{PROCESS_ID}.algoritmos-coord-service" # FQDN do Pod atual
    logger.info(f"Enviando REQUEST com TS={request_ts} para todos os pares.")
    async with httpx.AsyncClient(timeout=3.0) as client: # Timeout adicionado para debug
        for peer_name in PEERS:
            if peer_name == my_fqdn: # <--- COMPARAÇÃO SEGURA COM O FQDN COMPLETO
                continue
            
            url = f"http://{peer_name}:{PEER_PORT}/receive-request"
            payload = SCRequest(request_ts=request_ts, process_id=PROCESS_ID)
            try:
                await client.post(url, json=payload.dict(), timeout=5.0) 
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar REQUEST para {peer_name}: {e}")

async def send_reply(target_peer_id: int):
    """Envia uma mensagem de REPLY para um processo específico."""
    # Constrói o FQDN completo para o peer de destino
    target_peer_name = f"algoritmos-coord-{target_peer_id}.algoritmos-coord-service"
    logger.info(f"Enviando REPLY para {target_peer_name}.")
    
    url = f"http://{target_peer_name}:{PEER_PORT}/receive-reply"
    params = {"sender_id": PROCESS_ID}
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, params=params, timeout=5.0)
        except httpx.RequestError as e:
            logger.error(f"Falha ao enviar REPLY para {target_peer_name}: {e}")


# --- FUNÇÕES DE COMUNICAÇÃO PARA ELEIÇÃO (Q3) ---

async def send_election_to_higher_priority_peers():
    """Envia ELECTION para todos os processos com ID maior."""
    my_fqdn = f"algoritmos-coord-{PROCESS_ID}.algoritmos-coord-service"
    logger.info(f"P{PROCESS_ID} enviando ELECTION para processos com ID > {PROCESS_ID}.")
    
    async with httpx.AsyncClient() as client:
        for peer_name in PEERS:
            if peer_name == my_fqdn:
                continue
            
            # Extrai o ID do peer do nome FQDN (algoritmos-coord-{id}.algoritmos-coord-service)
            # Pega a parte antes do ponto e depois extrai o ID
            peer_hostname = peer_name.split('.')[0]  # "algoritmos-coord-{id}"
            peer_id = int(peer_hostname.split('-')[-1])  # Pega o último elemento após split por '-'
            
            # Só envia para peers com ID maior
            if peer_id > PROCESS_ID:
                url = f"http://{peer_name}:{PEER_PORT}/receive-election"
                params = {"candidate_id": PROCESS_ID}
                try:
                    await client.post(url, params=params, timeout=5.0)
                    logger.info(f"ELECTION enviado para P{peer_id}.")
                except httpx.RequestError as e:
                    logger.error(f"Falha ao enviar ELECTION para {peer_name}: {e}")


async def send_answer_to_peer(candidate_id: int):
    """Envia ANSWER para um processo candidato."""
    target_peer_name = f"algoritmos-coord-{candidate_id}.algoritmos-coord-service"
    logger.info(f"P{PROCESS_ID} enviando ANSWER para P{candidate_id}.")
    
    url = f"http://{target_peer_name}:{PEER_PORT}/receive-answer"
    params = {"peer_id": PROCESS_ID}
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(url, params=params, timeout=5.0)
        except httpx.RequestError as e:
            logger.error(f"Falha ao enviar ANSWER para {target_peer_name}: {e}")


async def send_coordinator_to_all_peers(leader_id: int):
    """Envia COORDINATOR para todos os processos."""
    my_fqdn = f"algoritmos-coord-{PROCESS_ID}.algoritmos-coord-service"
    logger.info(f"Enviando COORDINATOR (Líder: P{leader_id}) para todos os pares.")
    
    async with httpx.AsyncClient() as client:
        for peer_name in PEERS:
            if peer_name == my_fqdn:
                continue
            
            url = f"http://{peer_name}:{PEER_PORT}/receive-coordinator"
            params = {"leader_id": leader_id}
            
            try:
                await client.post(url, params=params, timeout=5.0)
            except httpx.RequestError as e:
                logger.error(f"Falha ao enviar COORDINATOR para {peer_name}: {e}")