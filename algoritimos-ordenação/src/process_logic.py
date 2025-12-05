import threading
import heapq
import os
import time
from typing import Dict, List, Any 
from src.models import Message 

# 1. Identificação do Processo
# O ID é lido da variável de ambiente injetada pelo K8s/StatefulSet
try:
    PROCESS_ID = int(os.environ.get('POD_NAME').split('-')[-1]) # Ex: 'processo-0' -> 0
except:
    PROCESS_ID = 99 # Fallback para testes locais

# 2. Relógio de Lamport (Logical Clock)
# Sorteamos um valor inicial conforme a dica da tarefa
LOGICAL_CLOCK: int = int(time.time() % 10) 

# 3. Fila de Prioridade (Pending Queue)
# heapq em Python implementa uma min-heap, ideal para fila de prioridade (menor valor primeiro)
# Formato: [(timestamp, sender_id, message_data), ...]
PENDING_QUEUE: List[Any] = [] 

# 4. Tabela de ACKs (Confirmações)
# Rastreia quantos ACKs uma mensagem específica recebeu.
# Chave: message_id (str), Valor: contador de ACKs (int)
ACK_TABLE: Dict[str, int] = {} 

# Mutex para proteger o acesso às estruturas de estado em ambiente concorrente (FastAPI)
STATE_LOCK = threading.Lock() 

# Porta padrão para comunicação entre Pods
PEER_PORT = 8080

# Endereços dos pares (definidos via variável de ambiente K8s)
# O nome do serviço 'algoritmos-svc' será adicionado depois para formar o FQDN
PEERS = ['algoritmos-coord-0', 'algoritmos-coord-1', 'algoritmos-coord-2'] 
TOTAL_PROCESSES = len(PEERS)

def update_clock(received_timestamp: int = 0) -> int:
    """Atualiza o relógio lógico de Lamport."""
    global LOGICAL_CLOCK
    with STATE_LOCK:
        if received_timestamp > LOGICAL_CLOCK:
            LOGICAL_CLOCK = received_timestamp + 1
        else:
            LOGICAL_CLOCK += 1
        return LOGICAL_CLOCK
    

async def receive_and_enqueue_message(message: Message):
    """Insere a mensagem na Fila de Prioridade e inicia o ACK."""
    from src.communication import send_acks_to_all_peers
    # 1. Atualizar o relógio lógico E CAPTURAR O NOVO VALOR
    new_ts = update_clock(message.timestamp) # <--- CORREÇÃO!

    # 2. Inserir na fila e contar o próprio ACK do remetente
    with STATE_LOCK:
        # AGORA, 'new_ts' existe e contém o timestamp que o processo P_receiver atribuiu à mensagem
        heapq.heappush(PENDING_QUEUE, (new_ts, message.sender_id, message)) 
        ACK_TABLE[message.message_id] = ACK_TABLE.get(message.message_id, 0) + 1 
        
    # 3. Enviar ACK para todos os processos (AGORA IMPLEMENTADO)
    await send_acks_to_all_peers(message.message_id) 

    # 4. Tentar processar as mensagens prontas
    try_to_process_messages()

def try_to_process_messages():
    """Tenta processar mensagens que já receberam todos os ACKs e estão no topo da fila."""
    
    # Continuar processando enquanto houver mensagens no topo que satisfazem a condição
    while PENDING_QUEUE:
        # A mensagem no topo é a que possui o menor timestamp
        timestamp, sender_id, message = PENDING_QUEUE[0]

        # 1. Verificar se a mensagem tem todos os ACKs
        acks_received = ACK_TABLE.get(message.message_id, 0)
        
        if acks_received >= TOTAL_PROCESSES:
            # Condição de Ordem Total Satisfeita:
            with STATE_LOCK:
                # 2. Remover da Fila (pop)
                processed_message = heapq.heappop(PENDING_QUEUE)
                # 3. Remover da Tabela de ACKs
                del ACK_TABLE[message.message_id]
            
            # 4. Processar a mensagem (representado por um print na tela)
            print(f"[{LOGICAL_CLOCK}] PROCESSADO! P{PROCESS_ID} > {message.content} (TS: {timestamp})")
            
        else:
            # A mensagem no topo não tem todos os ACKs. 
            # Nenhuma outra mensagem pode ser processada antes dela.
            break

def receive_ack(message_id: str):
    """Incrementa o contador de ACKs para uma mensagem específica e tenta processar."""
    
    # 1. Atualiza o relógio (recebimento de mensagem)
    update_clock() # Lamport sempre incrementa em eventos de recebimento.

    # 2. Incrementa o contador de ACKs
    with STATE_LOCK:
        ACK_TABLE[message_id] = ACK_TABLE.get(message_id, 0) + 1
        
    # 3. Tentar processar novamente, pois a contagem pode ter sido satisfeita
    try_to_process_messages()