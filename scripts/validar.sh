#!/usr/bin/env bash
# Validação de corretude exigida no Marco 2: prova de que as versões paralelas
# produzem EXATAMENTE o mesmo resultado do baseline.
#
# Compara a matriz de iterações inteira, byte a byte, com `cmp` — checksum
# sozinho não basta, somas podem colidir. Confere também o checksum impresso:
# uma corrida no acumulador erra a soma sem alterar a matriz. Sai com código
# != 0 se alguma configuração divergir, para poder ser usado em Makefile e em CI.
set -euo pipefail
cd "$(dirname "$0")/.."

TAM=${TAM:-"1000 1000 1000"}
THREADS=${THREADS:-"1 2 4 8"}
PROCESSOS=${PROCESSOS:-"1 2 3 4"}
OUT=$(mktemp -d)
trap 'rm -rf "$OUT"' EXIT

falhas=0
verifica() {
    local rotulo="$1" arquivo="$2" saida="$3"
    if ! cmp -s "$OUT/ref.bin" "$arquivo"; then
        local n
        n=$(cmp -l "$OUT/ref.bin" "$arquivo" 2>/dev/null | wc -l | tr -d ' ')
        echo "  FALHA $rotulo  ($n bytes diferentes)"
        falhas=$((falhas + 1))
    elif ! grep -qw "$ref_chk" "$saida"; then
        echo "  FALHA $rotulo  (matriz igual, mas $(grep -o 'checksum=[0-9]*' "$saida") em vez de $ref_chk)"
        falhas=$((falhas + 1))
    else
        echo "  OK    $rotulo"
    fi
}

echo "Referência: seq $TAM"
# shellcheck disable=SC2086
./bin/mandelbrot_seq $TAM --dump "$OUT/ref.bin" > "$OUT/ref.txt"
cat "$OUT/ref.txt"
ref_chk=$(grep -o 'checksum=[0-9]*' "$OUT/ref.txt")
echo

echo "OpenMP — o resultado não pode depender de threads nem de escalonamento:"
for t in $THREADS; do
    for s in static dynamic guided; do
        # shellcheck disable=SC2086
        OMP_NUM_THREADS=$t OMP_SCHEDULE=$s ./bin/mandelbrot_omp $TAM --dump "$OUT/omp.bin" > "$OUT/omp.txt"
        verifica "omp threads=$t schedule=$s" "$OUT/omp.bin" "$OUT/omp.txt"
    done
done
echo

echo "MPI — o resultado não pode depender de nprocs nem da decomposição:"
for d in bloco ciclica; do
    for p in $PROCESSOS; do
        # shellcheck disable=SC2086
        DECOMP=$d mpirun --oversubscribe -np "$p" ./bin/mandelbrot_mpi $TAM --dump "$OUT/mpi.bin" > "$OUT/mpi.txt"
        verifica "mpi np=$p decomp=$d" "$OUT/mpi.bin" "$OUT/mpi.txt"
    done
done
echo

if [ "$falhas" -eq 0 ]; then
    echo "TODAS AS CONFIGURAÇÕES BATEM COM O BASELINE, elemento a elemento e no checksum."
else
    echo "$falhas configuração(ões) divergem do baseline."
    exit 1
fi
