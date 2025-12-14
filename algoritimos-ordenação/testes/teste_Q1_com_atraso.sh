#!/bin/bash

# Script para testar a Q1 (Multicast com Ordem Total de Lamport) com atraso induzido.

# Função para limpar os processos em segundo plano ao sair
function cleanup() {
    echo ""
    echo "Encerrando..."
    # Usamos pkill para encontrar e matar os processos de port-forward pelo comando
    pkill -f "kubectl port-forward algoritmos-coord-0"
    pkill -f "kubectl port-forward algoritmos-coord-1"
    pkill -f "kubectl port-forward algoritmos-coord-2"
    echo "Processos de port-forward encerrados."
}

# A função cleanup será chamada quando o script terminar ou for interrompido
trap cleanup EXIT

echo "Iniciando teste da Q1 (com atraso)..."
echo "-------------------------------------------------"

# Inicia o port-forward para cada pod em segundo plano
echo "Iniciando port-forwards..."
kubectl port-forward algoritmos-coord-0 8080:8080 &
kubectl port-forward algoritmos-coord-1 8081:8080 &
kubectl port-forward algoritmos-coord-2 8082:8080 &

# Aguarda um tempo para garantir que os port-forwards estejam estabelecidos
echo "⏳ Aguardando 5 segundos para os port-forwards..."
sleep 5

# Envia as mensagens em paralelo
# A primeira mensagem para o processo 0 acionará o atraso no processo 2
echo "Enviando mensagem 01 (com atraso) do Processo 0..."
curl -s -X POST "http://127.0.0.1:8080/send?content=mensagem%20com%20atraso" &

# Mensagem 02 do processo 1
echo "Enviando mensagem 02 do Processo 1..."
curl -s -X POST "http://127.0.0.1:8081/send?content=mensagem%2002" &

# Mensagem 03 do processo 2
echo "Enviando mensagem 03 do Processo 2..."
curl -s -X POST "http://127.0.0.1:8082/send?content=mensagem%2003" &


# Aguarda o processamento, incluindo o atraso de 30s
echo "Aguardando 20 segundos para processamento (incluindo o atraso)..."
sleep 20

echo ""
echo "Coletando e processando os resultados..."

# Exibir logs de processamento
extract_processed_messages "algoritmos-coord-0" "Processo 0"
extract_processed_messages "algoritmos-coord-1" "Processo 1"
extract_processed_messages "algoritmos-coord-2" "Processo 2"

# Coletar todos os logs de processamento para ordenação cronológica
LOGS=""
for pod in algoritmos-coord-0 algoritmos-coord-1 algoritmos-coord-2; do
    pod_logs=$(kubectl logs "$pod" --since=2m --timestamps 2>/dev/null | grep "PROCESSADO" | awk -v p="$pod" '{print $1, $2, p, $0}')
    LOGS+="$pod_logs"$'\n'
done    


# Processa e exibe os logs em ordem cronológica
echo "================================================="
echo "        CRONOLOGIA DO PROCESSAMENTO (Q1 COM ATRASO)     "
echo "================================================="
echo "$LOGS" | sort -k1,2
echo "================================================="


# Limpar port-forwards
echo "Limpando port-forwards..."
kill $PF_PID_0 $PF_PID_1 $PF_PID_2 2>/dev/null
# Limpar os pods (criar novos para testes futuros)
echo "Reiniciando pods..."
kubectl delete pod algoritmos-coord-0 > /dev/null 2>&1
kubectl delete pod algoritmos-coord-1 > /dev/null 2>&1
kubectl delete pod algoritmos-coord-2 > /dev/null 2>&1


echo "Teste concluído."
