#!/bin/bash

# Script de teste para Q3 - Eleição de Líder com Algoritmo de Bully
# Este script simula a eleição de líder entre os 3 processos

echo "=========================================="
echo "  TESTE Q3 - ELEIÇÃO DE LÍDER (BULLY)"
echo "=========================================="

# Verificar se os pods estão rodando
echo "Verificando pods..."
kubectl get pods

# Setup das port-forwards para os 3 processos
echo ""
echo "Configurando port-forwards..."

# Process 0 -> porta 8080
kubectl port-forward pods/algoritmos-coord-0 8080:8080 > /dev/null 2>&1 &
PF_PID_0=$!

# Process 1 -> porta 8081
kubectl port-forward pods/algoritmos-coord-1 8081:8080 > /dev/null 2>&1 &
PF_PID_1=$!

# Process 2 -> porta 8082
kubectl port-forward pods/algoritmos-coord-2 8082:8080 > /dev/null 2>&1 &
PF_PID_2=$!

# Aguardar que as port-forwards sejam estabelecidas
sleep 2

echo "Port-forwards estabelecidas!"
echo ""

# Função para extrair e exibir logs de eleição
extract_election_logs() {
    local pod=$1
    local label=$2
    
    echo ""
    echo "--- Logs de Eleição do $label ---"
    kubectl logs "$pod" 2>/dev/null | grep -E "ELEIÇÃO|LÍDER|ELECTION|ANSWER|COORDINATOR|CANDIDAT" || echo "  (Nenhum log de eleição encontrado)"
}

# TESTE 1: Iniciar eleição no Processo 0 (com maior ID)
echo "=========================================="
echo "TESTE 1: Processo 0 inicia eleição"
echo "=========================================="
echo ""

curl -s -X POST http://127.0.0.1:8080/start-election

sleep 5

# Exibir logs de eleição
extract_election_logs "algoritmos-coord-0" "Processo 0 (Iniciador)"
extract_election_logs "algoritmos-coord-1" "Processo 1"
extract_election_logs "algoritmos-coord-2" "Processo 2 (ID mais alto)"

# TESTE 2: Limpar e iniciar eleição no Processo 1 (ID intermediário)
echo ""
echo "=========================================="
echo "TESTE 2: Limpar e Processo 1 inicia eleição"
echo "=========================================="
echo ""

# Limpar logs
kubectl delete pods --all > /dev/null 2>&1
sleep 5
kubectl get pods

# Reconfigurar port-forwards
kill $PF_PID_0 $PF_PID_1 $PF_PID_2 2>/dev/null

kubectl port-forward pods/algoritmos-coord-0 8080:8080 > /dev/null 2>&1 &
PF_PID_0=$!

kubectl port-forward pods/algoritmos-coord-1 8081:8080 > /dev/null 2>&1 &
PF_PID_1=$!

kubectl port-forward pods/algoritmos-coord-2 8082:8080 > /dev/null 2>&1 &
PF_PID_2=$!

sleep 2

echo "Port-forwards reestablecidas!"
echo ""

# Teste 2: Processo 1 inicia eleição
curl -s -X POST http://127.0.0.1:8081/start-election

sleep 5

# Exibir logs
extract_election_logs "algoritmos-coord-0" "Processo 0"
extract_election_logs "algoritmos-coord-1" "Processo 1 (Iniciador)"
extract_election_logs "algoritmos-coord-2" "Processo 2 (ID mais alto)"

# TESTE 3: Simular falha do líder - Processo 2 detecta falha e inicia eleição
echo ""
echo "=========================================="
echo "TESTE 3: Processo 2 detecta falha e inicia eleição"
echo "=========================================="
echo ""


# Matar Process 0 e 1 para simular falha
echo "Matando Processo 0 para simular falha do líder..."
kubectl delete pod algoritmos-coord-0 > /dev/null 2>&1
echo "Matando Processo 1 para simular falha do líder..."
kubectl delete pod algoritmos-coord-1 > /dev/null 2>&1

sleep 3

# Processo 2 tenta iniciar eleição (detectando que o líder caiu)
curl -s -X POST http://127.0.0.1:8082/start-election

sleep 5

# Exibir logs
echo ""
echo "--- Logs de Eleição do Processo 2 (Novo Líder Eleito) ---"
kubectl logs "algoritmos-coord-2" 2>/dev/null | grep -E "ELEIÇÃO|LÍDER|ELECTION|ANSWER|COORDINATOR|CANDIDAT|falha" || echo "  (Nenhum log de eleição encontrado)"

# Limpar port-forwards
echo ""
echo "=========================================="
echo "Limpando port-forwards..."
kill $PF_PID_0 $PF_PID_1 $PF_PID_2 2>/dev/null

# Limpar os pods (criar novos para testes futuros)
echo "Reiniciando pods..."
kubectl delete pod algoritmos-coord-0 > /dev/null 2>&1
kubectl delete pod algoritmos-coord-1 > /dev/null 2>&1
kubectl delete pod algoritmos-coord-2 > /dev/null 2>&1

echo "Teste Q3 finalizado!"

