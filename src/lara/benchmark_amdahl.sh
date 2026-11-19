
#!/bin/bash

REPETICOES=30
SAIDA="resultados_amdahl.csv"

echo "threads,execucao,tempo,checksum" > "$SAIDA"

for threads in 1 2 4 6 8 12 16; do

    echo "Testando $threads threads..."

    for ((i=1; i<=REPETICOES; i++)); do

        resultado=$(./openmp 400 600 1000 "$threads" 16) || exit 1

        tempo=$(echo "$resultado" | grep -o 'tempo=[^ ]*' | cut -d= -f2)
        checksum=$(echo "$resultado" | grep -o 'checksum=[^ ]*' | cut -d= -f2)

        if [[ "$checksum" != "41237493" || -z "$tempo" ]]; then
            echo "Erro: $resultado"
            exit 1
        fi

        echo "$threads,$i,$tempo,$checksum" >> "$SAIDA"

    done

    echo "$threads threads: concluido!"
done

echo "Resultados salvos em $SAIDA"


