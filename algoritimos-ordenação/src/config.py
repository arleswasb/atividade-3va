# src/config.py
import os

# --- Configurações de Ambiente e Identificação ---

# O ID do processo é lido da variável de ambiente 'POD_NAME' injetada pelo StatefulSet.
# Ex: 'algoritmos-coord-0' se torna o ID 0.
try:
    PROCESS_ID = int(os.environ.get('POD_NAME', 'fallback-99').split('-')[-1])
except (ValueError, AttributeError):
    PROCESS_ID = 99 # Fallback para testes locais ou ambientes não-k8s

# --- Configurações Gerais ---

# Tenta obter o ID do processo a partir das variáveis de ambiente.
# O nome do pod (ex: "algoritmos-coord-0") é passado pelo Downward API do K8s.
# Extrai o número do final do nome.
pod_name = os.getenv("POD_NAME", "algoritmos-coord-0")
PROCESS_ID = int(pod_name.split('-')[-1])

# Número total de processos no sistema distribuído.
TOTAL_PROCESSES = int(os.getenv("TOTAL_PROCESSES", 3))

# Porta padrão em que os processos pares (peers) escutam.
PEER_PORT = 8080

# Gera a lista de nomes de peers (ex: ['algoritmos-coord-0', 'algoritmos-coord-1', ...])
# Adiciona o nome do serviço ao final do nome do pod para usar o FQDN (Fully Qualified Domain Name)
# Ex: algoritmos-coord-0.algoritmos-coord-service
PEERS = [f"algoritmos-coord-{i}.algoritmos-coord-service" for i in range(TOTAL_PROCESSES)]

# --- Configurações de Rede ---

# Porta padrão para a API em cada Pod
PEER_PORT = 8080

# Lista de nomes de host dos processos pares.
# No Kubernetes, o StatefulSet garante que os pods tenham nomes estáveis e sequenciais.
# O Service 'algoritmos-svc' (headless) permite que esses nomes sejam resolvidos para os IPs dos pods.
# Gera a lista de nomes de peers (ex: ['algoritmos-coord-0', 'algoritmos-coord-1', ...])
# Adiciona o nome do serviço ao final do nome do pod para usar o FQDN (Fully Qualified Domain Name)
# Ex: algoritmos-coord-0.algoritmos-coord-service
PEERS = [f"algoritmos-coord-{i}.algoritmos-coord-service" for i in range(TOTAL_PROCESSES)]

# Número total de processos no sistema, usado para verificar a conclusão dos ACKs.
TOTAL_PROCESSES = len(PEERS)
