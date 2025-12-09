# Projeto de Sistemas Distribuídos - Atividade 3VA

Implementação completa de **3 algoritmos fundamentais de sistemas distribuídos** usando Python/FastAPI, Docker e Kubernetes.

## Conteúdo

- **Q1**: Multicast com Ordenação Total (Algoritmo de Lamport)
- **Q2**: Exclusão Mútua Distribuída (Algoritmo de Ricart & Agrawala)
- **Q3**: Eleição de Líder (Algoritmo de Bully)

---

## Arquitetura

### Infraestrutura
- **Plataforma**: Kubernetes (Minikube) + Docker
- **Aplicação**: FastAPI (Python 3.9)
- **Processos**: 3 replicas em StatefulSet (`algoritmos-coord-0`, `algoritmos-coord-1`, `algoritmos-coord-2`)
- **Rede**: Serviço headless para descoberta DNS (FQDNs: `algoritmos-coord-{id}.algoritmos-coord-service`)
- **Logging**: Loguru com formatação colorida

### Componentes do Projeto

```
projeto/
├── Dockerfile                 # Build da imagem Docker
├── requirements.txt           # Dependências Python
├── Readme.md                 # Este arquivo
│
├── src/                      # Código-fonte
│   ├── __init__.py
│   ├── main.py               # FastAPI server com todos os endpoints
│   ├── process_logic.py      # Lógica dos 3 algoritmos
│   ├── communication.py      # Comunicação inter-processos (HTTP)
│   ├── logger.py             # Sistema de logging
│   ├── config.py             # Configurações (IDs, portas, peers)
│   └── models.py             # Modelos Pydantic (Message, Ack, SCRequest, etc)
│
├── k8s/                      # Manifestos Kubernetes
│   ├── service.yaml          # Serviço headless
│   └── statefulset.yaml      # StatefulSet com 3 replicas
│
└── testes/                   # Scripts de teste
    ├── teste_Q1_sem_atraso.sh   # Teste Q1 (sem atraso)
    ├── teste_Q1_com_atraso.sh   # Teste Q1 (com delay no ACK)
    ├── teste_Q2.sh              # Teste Q2 (exclusão mútua)
    └── teste_Q3.sh              # Teste Q3 (eleição de líder)
```

---

## Questões Implementadas

### Q1: Multicast com Ordenação Total (Lamport)

**Objetivo**: Garantir que todas as mensagens sejam entregues a todos os processos na **mesma ordem causal**.

**Algoritmo**:
- Cada processo mantém um **relógio lógico de Lamport**
- Ao receber uma mensagem, o processo:
  1. Atualiza seu relógio: `max(relogio_local, timestamp_recebido) + 1`
  2. Enfileira a mensagem em uma **fila de prioridade** (por timestamp)
  3. Envia **ACKs** para confirmar o recebimento
- Quando todos os **TOTAL_PROCESSES** ACKs são recebidos, a mensagem pode ser processada

**Endpoints Q1**:
- `POST /send?content=...` - Envia mensagem para multicast
- `POST /message` - Recebe mensagem de outro processo
- `POST /ack` - Recebe confirmação (ACK)

**Testes Q1**:

*Teste sem atraso (comportamento normal):*
```bash
cd testes && bash teste_Q1_sem_atraso.sh
```

*Teste com atraso (cenário de estresse):*
```bash
cd testes && bash teste_Q1_com_atraso.sh
```

**Resultado esperado**: 
- 3 mensagens enviadas de diferentes processos
- **Ordem total garantida**: Todas as mensagens são processadas na mesma ordem em todos os processos
- Mesmo com atraso no ACK de P2 (teste com atraso), a ordenação é mantida
- Logs mostram: "PROCESSADO! Conteúdo: 'mensagem X' (TS=Y)"

---

### Q2: Exclusão Mútua Distribuída (Ricart & Agrawala)

**Objetivo**: Garantir que apenas **um processo por vez** acesse um recurso compartilhado.

**Algoritmo**:
- Processo que deseja acessar o recurso envia **REQUEST** com seu timestamp
- Outros processos respondem com **REPLY** se:
  - Não estão usando o recurso, OU
  - Estão esperando mas têm timestamp MAIOR (menor prioridade)
- Quando recebe **REPLIES de todos**, o processo entra na **região crítica**
- Ao sair, envia **REPLIES atrasadas** para processos que ficaram aguardando

**Endpoints Q2**:
- `POST /request-resource` - Solicita acesso ao recurso
- `POST /receive-request` - Recebe pedido de outro processo
- `POST /receive-reply` - Recebe autorização (REPLY)

**Teste Q2**:
```bash
cd testes && bash teste_Q2.sh
```

**Resultado esperado**:
- 2 processos solicitam recurso simultaneamente
- Processo com menor timestamp ganha acesso primeiro
- Logs mostram: "ACESSO OBTIDO! Entrando na Região Crítica"
- Exclusão mútua garantida (apenas 1 em seção crítica por vez)

---

### Q3: Eleição de Líder (Algoritmo de Bully)

**Objetivo**: Eleger um **novo líder** quando o processo com maior ID estiver disponível.

**Algoritmo**:
1. Processo `P0` inicia eleição → Envia `ELECTION` para `P1` e `P2`
2. `P1` vê que `1 > 0` → Responde `ANSWER` e inicia própria eleição
3. `P2` vê que `2 > 0` e `2 > 1` → Responde `ANSWER` e inicia eleição
4. `P2` não recebe resposta (ninguém com ID > 2) → **P2 é eleito LÍDER**
5. `P2` envia `COORDINATOR` notificando todos

**Endpoints Q3**:
- `POST /start-election` - Inicia eleição
- `POST /receive-election` - Recebe mensagem ELECTION
- `POST /receive-answer` - Recebe resposta ANSWER
- `POST /receive-coordinator` - Notificação de novo líder

**Teste Q3**:
```bash
cd testes && bash teste_Q3.sh
```

**Resultado esperado**:
- **Teste 1**: P0 inicia → P2 eleito (ID mais alto)
- **Teste 2**: P1 inicia → P2 eleito novamente
- **Teste 3**: P2 torna-se novo líder quando P0 e P1 caem
- Logs mostram: ">>> NOVO LÍDER ELEITO <<< P{id} é o novo LÍDER!"

---

## Como Executar

### Pré-requisitos

```bash
# Verificar instalações
docker --version          # v20+
minikube version          # v1.20+
kubectl version --client  # v1.20+
```

### 1. Iniciar Kubernetes

```bash
# Iniciar Minikube
minikube start

# Configurar Docker para usar Minikube
eval $(minikube docker-env)
```

### 2. Build da Imagem Docker

```bash
cd /home/arleswasb/Documentos/atividade\ 3va/algoritimos-ordenação
docker build -t algoritmos-distribuidos:latest .
```

### 3. Aplicar Manifestos Kubernetes

```bash
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/statefulset.yaml

# Verificar pods (aguardar "Running")
kubectl get pods -w
```

### 4. Executar Testes

```bash
cd testes

# Q1: Multicast com Ordem Total (sem atraso)
bash teste_Q1_sem_atraso.sh

# Q1: Multicast com Ordem Total (com atraso - teste de estresse)
bash teste_Q1_com_atraso.sh

# Q2: Exclusão Mútua
bash teste_Q2.sh

# Q3: Eleição de Líder
bash teste_Q3.sh
```

### 5. Monitorar Logs (Opcional)

```bash
# Terminal 1: Logs do Processo 0
kubectl logs -f algoritmos-coord-0

# Terminal 2: Logs do Processo 1
kubectl logs -f algoritmos-coord-1

# Terminal 3: Logs do Processo 2
kubectl logs -f algoritmos-coord-2
```

### 6. Limpar Ambiente

```bash
kubectl delete -f k8s/statefulset.yaml
kubectl delete -f k8s/service.yaml
minikube stop
```

---

## Detalhes de Implementação

### Relógio Lógico de Lamport
```python
def update_clock(received_timestamp: int = 0) -> int:
    global LOGICAL_CLOCK
    if received_timestamp > LOGICAL_CLOCK:
        LOGICAL_CLOCK = received_timestamp + 1
    else:
        LOGICAL_CLOCK += 1
    return LOGICAL_CLOCK
```

### Prioridade em Ricart & Agrawala
```python
# Responde OK se:
should_reply = (not RESOURCE_IN_USE and not WAITING_FOR_RESOURCE) or (
    WAITING_FOR_RESOURCE and (
        request_ts < REQUEST_TIMESTAMP or 
        (request_ts == REQUEST_TIMESTAMP and requester_id < PROCESS_ID)
    )
)
```

### Bully Algorithm - Resposta a ELECTION
```python
if PROCESS_ID > candidate_id:
    # Responde ANSWER e inicia própria eleição
    await send_answer_to_peer(candidate_id)
    if not ELECTION_IN_PROGRESS:
        await start_election()
```

---

## Verificação de Funcionamento

### Q1 - Ordem Total Mantida
```
Esperado: 3 mensagens processadas em ordem idêntica em todos os processos
Verificar: Logs mostram "PROCESSADO!" com timestamps crescentes
```

### Q2 - Exclusão Mútua
```
Esperado: Apenas 1 processo na seção crítica por vez
Verificar: Timespan entre "ACESSO OBTIDO!" e "SAINDO DA REGIÃO CRÍTICA" não sobrepostos
```

### Q3 - Eleição Correta
```
Esperado: Processo com ID mais alto se torna líder
Verificar: Logs mostram "P2 é o novo LÍDER" em todas as eleições
```

---

## Notas Importantes

1. **Timeout na Eleição**: 3 segundos - Se nenhuma resposta, o processo se torna líder
2. **Timeout em Requisições HTTP**: 5 segundos - Evita travamentos
3. **Fila de Prioridade (Q1)**: Ordena por `(timestamp, sender_id, message)`
4. **Deferred Replies (Q2)**: Respostas adiadas são enviadas quando o recurso é liberado
5. **FQDN dos Pods**: `algoritmos-coord-{id}.algoritmos-coord-service` (descoberta automática)

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| Port-forward falha | Verificar: `kubectl get pods \| grep Running` |
| Pods em `ImagePullBackOff` | Reconstruir imagem: `docker build -t algoritmos-distribuidos:latest .` |
| Curl: `Connection refused` | Aguardar pods iniciarem: `kubectl get pods -w` |
| Logs vazios | Adicionar delay no script: `sleep 2` após iniciar testes |

---

## Arquivos Principais

| Arquivo | Responsabilidade |
|---------|------------------|
| `main.py` | 12 endpoints FastAPI (4 por questão) |
| `process_logic.py` | 20+ funções de lógica dos algoritmos |
| `communication.py` | Funções de envio HTTP/FQDN entre processos |
| `config.py` | IDs, portas, FQDNs dos peers |
| `logger.py` | Logging colorido com `loguru` |
| `models.py` | Modelos: Message, Ack, SCRequest |

---
