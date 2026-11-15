#!/bin/bash

REPETICOES=1000
SAIDA="resultados_benchmark.csv"

echo "versao,modelo,execucao,tempo,calculo,comunicacao,desbalanceamento,checksum" > "$SAIDA"

executar_teste() {
    local versao="$1"
    local modelo="$2"
    shift 2

    echo "Testando $versao - $modelo..."

    for ((i=1; i<=REPETICOES; i++)); do
        resultado=$("$@")

        tempo=$(echo "$resultado" | grep -o 'tempo=[^ ]*' | cut -d= -f2)
        calculo=$(echo "$resultado" | grep -o 'calculo=[^ ]*' | cut -d= -f2)
        comunicacao=$(echo "$resultado" | grep -o 'comunicacao=[^ ]*' | cut -d= -f2)
        desbalanceamento=$(echo "$resultado" | grep -o 'desbalanceamento=[^ ]*' | cut -d= -f2)
        checksum=$(echo "$resultado" | grep -o 'checksum=[^ ]*' | cut -d= -f2)

        echo "$versao,$modelo,$i,$tempo,$calculo,$comunicacao,$desbalanceamento,$checksum" >> "$SAIDA"
    done
}

# SEQUENCIAL
executar_teste sequencial unico ./sequencial 400 600 1000

# OPENMP

executar_teste openmp todos ./openmp 400 600 1000 4 16

# MPI
executar_teste mpi todos mpirun --allow-run-as-root --oversubscribe -np 4 ./mpi 400 600 1000 todos ciclica
executar_teste mpi mestre mpirun --allow-run-as-root --oversubscribe -np 5 ./mpi 400 600 1000 mestre ciclica

# HIBRIDO
executar_teste hibrido todos mpirun --allow-run-as-root --oversubscribe -np 3 ./hibrido 400 600 1000 todos ciclica 2 16
executar_teste hibrido mestre mpirun --allow-run-as-root --oversubscribe -np 3 ./hibrido 400 600 1000 mestre ciclica 2 1


echo "Testes finalizados! Resultados em $SAIDA"
