#!/bin/bash

# Script para testar o algoritmo de Exclusão Mútua (Q2) e exibir um resumo cronológico.

echo "Iniciando teste de Exclusão Mútua (Q2)..."
echo "-------------------------------------------------"



# Inicia os port-forwards em background
echo "Iniciando port-forward para o Pod 0 (localhost:8080)..."
kubectl port-forward algoritmos-coord-0 8080:8080 > /dev/null 2>&1 &
PID1=$!

echo "Iniciando port-forward para o Pod 2 (localhost:8082)..."
kubectl port-forward algoritmos-coord-2 8082:8080 > /dev/null 2>&1 &
PID2=$!

# Garante que os processos de port-forward sejam encerrados ao final do script
trap "echo 'Encerrando port-forwards...'; kill $PID1; kill $PID2; exit" INT TERM EXIT

echo "Aguardando 3 segundos para os port-forwards estabilizarem..."
sleep 3

echo "Enviando pedidos de recurso concorrentes para o Pod 0 e Pod 2!"
# Dispara as requisições em background para simular concorrência
(curl -s -X POST http://127.0.0.1:8080/request-resource) &
(curl -s -X POST http://127.0.0.1:8082/request-resource) &

echo ""
echo "Aguardando 15 segundos para a execução completa do algoritmo..."
sleep 15

echo ""
echo "Coletando e processando os resultados..."
echo "================================================="
echo "          CRONOLOGIA DOS EVENTOS (Q2)            "
echo "================================================="

# Coleta os logs de todos os pods, filtra as linhas importantes, e ordena pela coluna de tempo (o timestamp do loguru)
(kubectl logs algoritmos-coord-0 & kubectl logs algoritmos-coord-1 & kubectl logs algoritmos-coord-2) | \
grep -E "Pedindo acesso|Adiado pedido|ACESSO OBTIDO|TRABALHO CONCLUÍDO|Enviando REPLY para" | \
sort -k 1,1

echo "Limpando port-forwards..."
kill $PF_PID_0 $PF_PID_1 $PF_PID_2 2>/dev/null
# Limpar os pods (criar novos para testes futuros)
echo "Reiniciando pods..."
kubectl delete pod algoritmos-coord-0 > /dev/null 2>&1
kubectl delete pod algoritmos-coord-1 > /dev/null 2>&1
kubectl delete pod algoritmos-coord-2 > /dev/null 2>&1

echo "================================================="
echo "Teste concluído."
echo ""


# O trap no início do script cuidará de encerrar os PIDs.