import asyncio
import httpx
from typing import List
import json

# Importa as constantes dos pares
from src.process_logic import PEERS, PROCESS_ID, PEER_PORT

async def send_async_requests(targets: List[str], endpoint: str, payload: dict):
    """
    Função genérica para enviar requisições POST assíncronas para múltiplos processos.
    
    Args:
        targets: Lista de nomes de hosts (ex: 'algoritmos-coord-0').
        endpoint: O endpoint da API (ex: '/ack').
        payload: O corpo da requisição.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = []
        for target_host in targets:
            # Constrói o FQDN (Fully Qualified Domain Name) para o Pod
            fqdn = f"{target_host}.algoritmos-svc"
            url = f"http://{fqdn}:{PEER_PORT}{endpoint}"
            
            # log apenas para debug
            # print(f"P{PROCESS_ID} enviando {endpoint} para {fqdn}...")
            
            tasks.append(client.post(url, json=payload))
        
        # Executa todas as chamadas de rede em paralelo
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

# Funções específicas para o Multicast
async def send_acks_to_all_peers(message_id: str):
    """Dispara o envio assíncrono do ACK para todos os pares."""
    
    # O payload do ACK é simples: o ID da mensagem
    payload = {"message_id": message_id} 
    
    # Envia o ACK para todos os processos, incluindo a si mesmo, para consistência.
    # A lógica de recebimento de ACK já lida com isso.
    await send_async_requests(PEERS, "/ack", payload)
    # O print foi movido para a lógica de recebimento para refletir o evento real.