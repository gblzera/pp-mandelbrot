
#!/bin/bash

set -euo pipefail

REPETICOES=30
SAIDA="resultados_escalabilidade_mpi_hibrido.csv"
CHECKSUM_ESPERADO="41237493"

echo "versao,modelo,ranks,threads_por_rank,trabalhadores,recursos_calculo,execucao,tempo,calculo,comunicacao,desbalanceamento,checksum" > "$SAIDA"

extrair() {
    echo "$1" | grep -o "$2=[^ ]*" | cut -d= -f2
}

executar() {
    local versao="$1"
    local modelo="$2"
    local ranks="$3"
    local threads="$4"
    local trabalhadores="$5"
    shift 5

    local recursos_calculo=$((trabalhadores * threads))

    echo "Testando $versao $modelo: $ranks ranks, $threads threads/rank..."

    for ((i=1; i<=REPETICOES; i++)); do
        resultado=$("$@")

        tempo=$(extrair "$resultado" tempo)
        calculo=$(extrair "$resultado" calculo)
        comunicacao=$(extrair "$resultado" comunicacao)
        desbalanceamento=$(extrair "$resultado" desbalanceamento)
        checksum=$(extrair "$resultado" checksum)

        if [[ "$checksum" != "$CHECKSUM_ESPERADO" || -z "$tempo" ]]; then
            echo "Erro na execucao $i: $resultado"
            exit 1
        fi

        echo "$versao,$modelo,$ranks,$threads,$trabalhadores,$recursos_calculo,$i,$tempo,$calculo,$comunicacao,$desbalanceamento,$checksum" >> "$SAIDA"
    done

    echo "Concluido!"
}

# MPI: todos os ranks calculam
for ranks in 1 2 4 6 8 12 16; do
    executar mpi todos "$ranks" 1 "$ranks" \
        mpirun --oversubscribe -np "$ranks" \
        ./mpi 400 600 1000 todos ciclica
done

# MPI: rank 0 apenas coordena
for ranks in 2 3 5 7 9 13 17; do
    executar mpi mestre "$ranks" 1 "$((ranks-1))" \
        mpirun --oversubscribe -np "$ranks" \
        ./mpi 400 600 1000 mestre ciclica
done

# Hibrido: 2 threads por rank
for ranks in 1 2 3 4 6 8; do
    executar hibrido todos "$ranks" 2 "$ranks" \
        mpirun --oversubscribe -np "$ranks" \
        ./hibrido 400 600 1000 todos ciclica 2 16
done

# Hibrido mestre: rank 0 nao calcula
for ranks in 2 3 4 5 7 9; do
    executar hibrido mestre "$ranks" 2 "$((ranks-1))" \
        mpirun --oversubscribe -np "$ranks" \
        ./hibrido 400 600 1000 mestre ciclica 2 16
done

echo "Testes finalizados!"
echo "Resultados salvos em $SAIDA"
