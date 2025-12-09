import threading
import heapq
import time
import asyncio
from typing import Dict, List, Any
from src.models import Message
from src.logger import logger
from src.config import TOTAL_PROCESSES, PROCESS_ID

# --- Estado do Processo ---

# 1. Relógio de Lamport (Logical Clock)
LOGICAL_CLOCK: int = int(time.time() % 10)

# 2. Fila de Prioridade (Pending Queue) - para Multicast Q1
PENDING_QUEUE: List[Any] = []

# 3. Tabela de ACKs (Confirmações) - para Multicast Q1
ACK_TABLE: Dict[str, int] = {}

# Mutex para proteger o acesso concorrente às estruturas de estado
STATE_LOCK = threading.Lock()

# --- Estado para Exclusão Mútua (Q2) ---
RESOURCE_IN_USE = False
WAITING_FOR_RESOURCE = False
REQUEST_TIMESTAMP = -1
PENDING_REPLIES_COUNT = 0
# Fila para guardar pedidos (process_id) que chegaram enquanto usávamos o recurso
DEFERRED_REPLIES: List[int] = []
REPLY_EVENT = asyncio.Event()

# --- Estado para Eleição de Líder (Q3 - Algoritmo de Bully) ---
# Estados possíveis: "FOLLOWER", "CANDIDATE", "LEADER"
LEADER_STATE = "FOLLOWER"
CURRENT_LEADER = None  # ID do líder atual (None se desconhecido)
ELECTION_IN_PROGRESS = False
ELECTION_ANSWERS_RECEIVED: List[int] = []  # Processos que responderam à eleição
HIGHEST_PRIORITY_ID = -1  # ID mais alto visto durante eleição

# --- Funções de Lógica do Algoritmo de Multicast (Q1) ---

def update_clock(received_timestamp: int = 0) -> int:
    """Atualiza o relógio lógico de Lamport."""
    global LOGICAL_CLOCK
    with STATE_LOCK:
        old_clock = LOGICAL_CLOCK
        if received_timestamp > LOGICAL_CLOCK:
            LOGICAL_CLOCK = received_timestamp + 1
        else:
            LOGICAL_CLOCK += 1
        logger.debug(f"Clock updated: {old_clock} -> {LOGICAL_CLOCK} (recebido: {received_timestamp})")
        return LOGICAL_CLOCK

async def receive_and_enqueue_message(message: Message):
    """Processa uma mensagem de multicast recebida."""
    from src.communication import send_acks_to_all_peers
    
    new_ts = update_clock(message.timestamp)

    with STATE_LOCK:
        heapq.heappush(PENDING_QUEUE, (new_ts, message.sender_id, message))
        ACK_TABLE[message.message_id] = ACK_TABLE.get(message.message_id, 0) + 1
        logger.info(f"Mensagem {message.message_id} enfileirada com TS={new_ts}. ACK inicial: 1.")

    await send_acks_to_all_peers(message.message_id)
    try_to_process_messages()

def try_to_process_messages():
    """Verifica se a mensagem no topo da fila de prioridade pode ser processada."""
    while PENDING_QUEUE:
        with STATE_LOCK:
            if not PENDING_QUEUE:
                break
            timestamp, sender_id, message = PENDING_QUEUE[0]
            acks_received = ACK_TABLE.get(message.message_id, 0)

        if acks_received >= TOTAL_PROCESSES:
            with STATE_LOCK:
                processed_message_tuple = heapq.heappop(PENDING_QUEUE)
                if message.message_id in ACK_TABLE:
                    del ACK_TABLE[message.message_id]
            
            p_msg = processed_message_tuple[2]
            logger.success(
                f"PROCESSADO! Conteúdo: '{p_msg.content}' "
                f"(ID: {p_msg.message_id}, TS Original: {p_msg.timestamp}, TS Final: {timestamp})"
            )
        else:
            break

def receive_ack(message_id: str):
    """Processa um ACK recebido de outro processo."""
    update_clock()
    
    with STATE_LOCK:
        if message_id in ACK_TABLE:
            ACK_TABLE[message_id] += 1
            logger.info(f"Contador de ACK para {message_id} incrementado para {ACK_TABLE[message_id]}.")
        else:
            ACK_TABLE[message_id] = 1
            logger.warning(f"ACK recebido para {message_id} antes da mensagem. Tabela iniciada com 1.")

    try_to_process_messages()


# --- Funções de Lógica para Exclusão Mútua (Q2) ---

async def request_resource_access():
    """Inicia a solicitação de acesso à região crítica."""
    from src.communication import send_request_to_peers
    global WAITING_FOR_RESOURCE, REQUEST_TIMESTAMP, PENDING_REPLIES_COUNT, LOGICAL_CLOCK
    
    # 1. Obter o novo timestamp FORA do lock (boa prática)
    current_ts = update_clock()

    with STATE_LOCK:
        if RESOURCE_IN_USE or WAITING_FOR_RESOURCE:
            logger.warning("Pedido de recurso ignorado: já está em uso ou na fila.")
            return

        WAITING_FOR_RESOURCE = True
        REQUEST_TIMESTAMP = current_ts
        PENDING_REPLIES_COUNT = TOTAL_PROCESSES - 1
        REPLY_EVENT.clear()
        logger.info(f"Pedindo acesso ao recurso com TS={REQUEST_TIMESTAMP}. Faltam {PENDING_REPLIES_COUNT} respostas.")

    await send_request_to_peers(REQUEST_TIMESTAMP)
    
    # Se não houver outros processos, entra direto
    if PENDING_REPLIES_COUNT == 0:
        await enter_critical_section()
        return
    
    # AGORA BLOQUEIA ATÉ QUE TODOS OS REPLYS CHEGUEM!
    logger.info("Aguardando todas as respostas (REPLYs)...")
    await REPLY_EVENT.wait() 

    # Quando o wait() retornar, significa que PENDING_REPLIES_COUNT == 0
    await enter_critical_section()

async def handle_resource_request(request_ts: int, requester_id: int):
    """Lida com um pedido de recurso vindo de outro processo."""
    from src.communication import send_reply
    update_clock(request_ts)
    with STATE_LOCK:
        # Regra de Ricart & Agrawala
        # Responde OK se:
        # 1. Não estamos usando nem querendo o recurso.
        # 2. Estamos esperando, mas nosso timestamp é MAIOR (menor prioridade).
        # 3. Estamos esperando com o mesmo timestamp, mas nosso ID é MAIOR (menor prioridade).
        should_reply = (
            not RESOURCE_IN_USE and not WAITING_FOR_RESOURCE
        ) or (
            WAITING_FOR_RESOURCE and (request_ts < REQUEST_TIMESTAMP or (request_ts == REQUEST_TIMESTAMP and requester_id < PROCESS_ID))
        )

        if should_reply:
            logger.info(f"Respondendo OK para P{requester_id} (TS do pedido: {request_ts})")
            # O envio da resposta é feito fora do lock para não bloquear
        else:
            logger.warning(f"Adiado pedido de P{requester_id} (TS: {request_ts}). Nosso TS: {REQUEST_TIMESTAMP}")
            DEFERRED_REPLIES.append(requester_id)
            # Não envia resposta agora

    if should_reply:
        await send_reply(requester_id)


async def handle_reply():
    """Processa uma mensagem de REPLY recebida."""
    global PENDING_REPLIES_COUNT
    
    with STATE_LOCK:
        if WAITING_FOR_RESOURCE:
            PENDING_REPLIES_COUNT -= 1
            logger.info(f"REPLY recebido. Faltam {PENDING_REPLIES_COUNT} respostas.")
            
            if PENDING_REPLIES_COUNT == 0:
                # Dispara o evento para desbloquear a função request_resource_access
                REPLY_EVENT.set() # <--- NOVO: Sinaliza a conclusão
        else:
            logger.warning("REPLY recebido, mas não estava esperando. Ignorando.")
            return


async def enter_critical_section():
    """Simula a entrada e o trabalho na seção crítica."""
    global WAITING_FOR_RESOURCE, RESOURCE_IN_USE
    
    with STATE_LOCK:
        WAITING_FOR_RESOURCE = False
        RESOURCE_IN_USE = True
    
    logger.success(">>> ACESSO OBTIDO! Entrando na Região Crítica. <<<")
    
    # Simula trabalho
    await asyncio.sleep(5) 
    
    logger.success(">>> TRABALHO CONCLUÍDO! Saindo da Região Crítica. <<<")
    await release_resource()


async def release_resource():
    """Libera o recurso e responde a todos os pedidos adiados."""
    from src.communication import send_reply
    global RESOURCE_IN_USE, DEFERRED_REPLIES
    
    deferred_to_reply = []
    with STATE_LOCK:
        RESOURCE_IN_USE = False
        # Move os pedidos pendentes para uma lista local para responder fora do lock
        deferred_to_reply.extend(DEFERRED_REPLIES)
        DEFERRED_REPLIES.clear()
        logger.info(f"Recurso liberado. Enviando {len(deferred_to_reply)} respostas adiadas.")

    # Envia todas as respostas adiadas
    for requester_id in deferred_to_reply:
        await send_reply(requester_id)


# --- Funções para Eleição de Líder (Q3 - Algoritmo de Bully) ---

async def start_election():
    """Inicia uma eleição de líder usando o Algoritmo de Bully."""
    from src.communication import send_election_to_higher_priority_peers
    global ELECTION_IN_PROGRESS, LEADER_STATE, CURRENT_LEADER, ELECTION_ANSWERS_RECEIVED, HIGHEST_PRIORITY_ID
    
    with STATE_LOCK:
        if ELECTION_IN_PROGRESS:
            logger.warning("Uma eleição já está em progresso.")
            return
        
        ELECTION_IN_PROGRESS = True
        LEADER_STATE = "CANDIDATE"
        ELECTION_ANSWERS_RECEIVED = []
        HIGHEST_PRIORITY_ID = PROCESS_ID
        logger.info(f">>> INICIANDO ELEIÇÃO <<< P{PROCESS_ID} está se candidatando a líder.")

    # Envia ELECTION para todos os processos com ID maior
    await send_election_to_higher_priority_peers()
    
    # Aguarda respostas por um tempo fixo (timeout)
    timeout = 3  # segundos
    logger.info(f"Aguardando respostas por {timeout}s...")
    await asyncio.sleep(timeout)
    
    # Se nenhum processo respondeu, este processo vira o líder
    with STATE_LOCK:
        if len(ELECTION_ANSWERS_RECEIVED) == 0:
            logger.success(f">>> NOVO LÍDER ELEITO <<< P{PROCESS_ID} é o novo LÍDER!")
            LEADER_STATE = "LEADER"
            CURRENT_LEADER = PROCESS_ID
            ELECTION_IN_PROGRESS = False
        else:
            logger.info(f"Eleição em progresso: {len(ELECTION_ANSWERS_RECEIVED)} processos responderam.")
            LEADER_STATE = "FOLLOWER"
            ELECTION_IN_PROGRESS = False
            return

    # Se este processo se tornou líder, notifica todos os outros
    if LEADER_STATE == "LEADER":
        await broadcast_coordinator(PROCESS_ID)


async def handle_election_message(candidate_id: int):
    """Recebe uma mensagem de ELECTION de um processo candidato."""
    from src.communication import send_answer_to_peer
    global ELECTION_ANSWERS_RECEIVED, LEADER_STATE, ELECTION_IN_PROGRESS
    
    logger.info(f"Recebido ELECTION de P{candidate_id}.")
    
    # Se o nosso ID é maior, respondemos ANSWER e iniciamos nossa própria eleição
    if PROCESS_ID > candidate_id:
        logger.info(f"P{PROCESS_ID} > P{candidate_id}: Respondendo ANSWER e iniciando eleição própria.")
        await send_answer_to_peer(candidate_id)
        
        # Inicia eleição deste processo se ainda não há uma em progresso
        if not ELECTION_IN_PROGRESS:
            await start_election()
    else:
        logger.info(f"P{PROCESS_ID} <= P{candidate_id}: Não respondendo. Aguardando COORDINATOR.")


async def handle_answer_message(peer_id: int):
    """Recebe uma mensagem de ANSWER durante uma eleição."""
    global ELECTION_ANSWERS_RECEIVED, HIGHEST_PRIORITY_ID
    
    with STATE_LOCK:
        if peer_id not in ELECTION_ANSWERS_RECEIVED:
            ELECTION_ANSWERS_RECEIVED.append(peer_id)
            if peer_id > HIGHEST_PRIORITY_ID:
                HIGHEST_PRIORITY_ID = peer_id
            logger.info(f"ANSWER recebido de P{peer_id}. Total de respostas: {len(ELECTION_ANSWERS_RECEIVED)}")


async def handle_coordinator_message(leader_id: int):
    """Recebe notificação de um novo líder."""
    global CURRENT_LEADER, LEADER_STATE, ELECTION_IN_PROGRESS
    
    with STATE_LOCK:
        CURRENT_LEADER = leader_id
        LEADER_STATE = "FOLLOWER"
        ELECTION_IN_PROGRESS = False
        logger.success(f">>> NOVO LÍDER ELEITO <<< P{leader_id} é o novo LÍDER (notificado para P{PROCESS_ID}).")


async def broadcast_coordinator(leader_id: int):
    """Envia COORDINATOR para todos os processos."""
    from src.communication import send_coordinator_to_all_peers
    logger.info(f"P{PROCESS_ID} (líder) notificando todos sobre sua eleição...")
    await send_coordinator_to_all_peers(leader_id)

