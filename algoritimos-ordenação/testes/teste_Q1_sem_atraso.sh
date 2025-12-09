#!/bin/bash

# Script de teste para Q1 - Multicast com Ordenação Total SEM ATRASO
# Este script demonstra que mesmo sem atrasos, a ordem total é mantida

echo "=========================================="
echo "  TESTE Q1 - MULTICAST SEM ATRASO"
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

echo "=========================================="
echo "Enviando 3 mensagens rapidamente"
echo "=========================================="
echo ""

# Enviar 3 mensagens rapidamente de diferentes processos
echo "Enviando mensagem 01 de P0..."
curl -s -X POST "http://127.0.0.1:8080/send?content=mensagem%2001" > /dev/null

sleep 0.5

echo "Enviando mensagem 02 de P1..."
curl -s -X POST "http://127.0.0.1:8081/send?content=mensagem%2002" > /dev/null

sleep 0.5

echo "Enviando mensagem 03 de P2..."
curl -s -X POST "http://127.0.0.1:8082/send?content=mensagem%2003" > /dev/null

echo ""
echo "Aguardando processamento das mensagens (5 segundos)..."
sleep 5

echo ""
echo "=========================================="
echo "RESULTADO: Mensagens Processadas por Processo"
echo "=========================================="
echo ""

# Função para extrair e exibir logs de processamento
extract_processed_messages() {
    local pod=$1
    local label=$2
    
    echo "--- $label ---"
    kubectl logs "$pod" 2>/dev/null | grep "PROCESSADO" | sed 's/^/  /'
    echo ""
}

# Exibir logs de processamento
extract_processed_messages "algoritmos-coord-0" "Processo 0"
extract_processed_messages "algoritmos-coord-1" "Processo 1"
extract_processed_messages "algoritmos-coord-2" "Processo 2"

echo "=========================================="
echo "Análise:"
echo "=========================================="
echo "✓ Se as 3 mensagens aparecem na MESMA ORDEM em todos os processos,"
echo "  então a ordem total foi mantida corretamente!"
echo ""

# Limpar port-forwards
echo "Limpando port-forwards..."
kill $PF_PID_0 $PF_PID_1 $PF_PID_2 2>/dev/null

echo ""
echo "Teste Q1 (sem atraso) finalizado!"
