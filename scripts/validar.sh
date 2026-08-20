#!/usr/bin/env bash
# Validação de corretude exigida no Marco 2: prova de que as versões paralelas
# produzem EXATAMENTE o mesmo resultado do baseline.
#
# Não compara checksum (somas podem colidir): compara a matriz de iterações
# inteira, byte a byte, com `cmp`. Sai com código != 0 no primeiro desvio, para
# poder ser usado em Makefile e em CI.
set -euo pipefail
cd "$(dirname "$0")/.."

TAM=${TAM:-"1000 1000 1000"}
THREADS=${THREADS:-"1 2 4 8"}
PROCESSOS=${PROCESSOS:-"1 2 3 4"}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

falhas=0
verifica() {
    local rotulo="$1" arquivo="$2"
    if cmp -s "$OUT/ref.bin" "$arquivo"; then
        echo "  OK    $rotulo"
    else
        local n
        n=$(cmp -l "$OUT/ref.bin" "$arquivo" 2>/dev/null | wc -l | tr -d ' ')
        echo "  FALHA $rotulo  ($n bytes diferentes)"
        falhas=$((falhas + 1))
    fi
}

echo "Referência: seq $TAM"
# shellcheck disable=SC2086
./bin/mandelbrot_seq $TAM --dump "$OUT/ref.bin" > "$OUT/ref.txt"
cat "$OUT/ref.txt"
echo

echo "OpenMP — o resultado não pode depender de threads nem de escalonamento:"
for t in $THREADS; do
    for s in static dynamic guided; do
        # shellcheck disable=SC2086
        OMP_NUM_THREADS=$t OMP_SCHEDULE=$s ./bin/mandelbrot_omp $TAM --dump "$OUT/omp.bin" > /dev/null
        verifica "omp threads=$t schedule=$s" "$OUT/omp.bin"
    done
done
echo

echo "MPI — o resultado não pode depender de nprocs nem da decomposição:"
for d in bloco ciclica; do
    for p in $PROCESSOS; do
        # shellcheck disable=SC2086
        DECOMP=$d mpirun --oversubscribe -np "$p" ./bin/mandelbrot_mpi $TAM --dump "$OUT/mpi.bin" > /dev/null
        verifica "mpi np=$p decomp=$d" "$OUT/mpi.bin"
    done
done
echo

if [ "$falhas" -eq 0 ]; then
    echo "TODAS AS CONFIGURAÇÕES BATEM COM O BASELINE, elemento a elemento."
else
    echo "$falhas configuração(ões) divergem do baseline."
    exit 1
fi
