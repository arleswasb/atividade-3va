#!/bin/bash

# Script para automatizar o deploy da aplicação no Minikube

# Aborta o script se qualquer comando falhar
set -e

echo "--- 1. Configurando ambiente Docker do Minikube ---"
# O comando 'eval' precisa ser executado no seu shell, então vamos apenas exibir a instrução.
echo "Por favor, execute 'eval \$(minikube docker-env)' no seu terminal antes de continuar, se ainda não o fez."
eval $(minikube docker-env)

# Navega para o diretório raiz do projeto a partir do diretório do script
# Isso garante que o 'docker build' encontre o Dockerfile
cd "$(dirname "$0")/.."

echo ""
echo "--- 2. Construindo a imagem Docker: algoritmos-av2:v3 ---"
docker build -t algoritmos-av2:v3 .

echo ""
echo "--- 3. Aplicando manifestos do Kubernetes ---"
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/statefulset.yaml

echo ""
echo "--- Deploy concluído! ---"
echo "Use 'kubectl get pods' para verificar o status."
echo "Use 'kubectl logs -f <pod-name>' para ver os logs."
