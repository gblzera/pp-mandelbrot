#!/usr/bin/env bash
# Campanha de medição -> resultados/medicoes.csv
#
# Protocolo: cada configuração roda REPETICOES vezes, após AQUECIMENTO execuções
# descartadas. Registra escalabilidade FORTE (entrada fixa, mais workers) e
# FRACA (entrada cresce com os workers, carga por worker constante).
# Rodar no ambiente de referência (laboratório ou contêiner Docker).
set -euo pipefail
cd "$(dirname "$0")/.."

REPETICOES=${REPETICOES:-5}
AQUECIMENTO=${AQUECIMENTO:-1}
TAMANHOS=("1000 1000 1000" "2000 2000 1000" "4000 4000 1000")
THREADS=(1 2 4 8)
PROCESSOS=(1 2 4)
ESCALONAMENTOS=(static dynamic guided)
DECOMPOSICOES=(bloco ciclica)
LADO_BASE=${LADO_BASE:-1000}      # escalabilidade fraca
MAX_ITER_FRACA=1000

SAIDA=resultados/medicoes.csv
mkdir -p resultados
echo "experimento,versao,config,variante,largura,altura,max_iter,repeticao,checksum,tempo,calculo,comunicacao,desbalanceamento" > "$SAIDA"

campo() { grep -o "$2=[^ ]*" <<< "$1" | cut -d= -f2 || true; }

# executa <experimento> <versao> <config> <variante> "<L A M>" <comando...>
executa() {
    local exp="$1" versao="$2" config="$3" variante="$4" tam="$5"; shift 5
    local L A M linha
    read -r L A M <<< "$tam"
    for ((r = -AQUECIMENTO; r < REPETICOES; r++)); do
        linha=$("$@" "$L" "$A" "$M")
        ((r < 0)) && continue
        printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
            "$exp" "$versao" "$config" "$variante" "$L" "$A" "$M" "$r" \
            "$(campo "$linha" checksum)" "$(campo "$linha" tempo)" \
            "$(campo "$linha" calculo)" "$(campo "$linha" comunicacao)" \
            "$(campo "$linha" desbalanceamento)" >> "$SAIDA"
    done
    echo "  ok: $exp $versao config=$config ${variante} ${L}x${A}"
}

echo "== Escalabilidade forte =="
for tam in "${TAMANHOS[@]}"; do
    executa forte seq 1 - "$tam" ./bin/mandelbrot_seq
    for s in "${ESCALONAMENTOS[@]}"; do
        for t in "${THREADS[@]}"; do
            executa forte omp "$t" "$s" "$tam" \
                env OMP_SCHEDULE="$s" OMP_NUM_THREADS="$t" ./bin/mandelbrot_omp
        done
    done
    for d in "${DECOMPOSICOES[@]}"; do
        for p in "${PROCESSOS[@]}"; do
            executa forte mpi "$p" "$d" "$tam" \
                env DECOMP="$d" mpirun --oversubscribe -np "$p" ./bin/mandelbrot_mpi
        done
    done
done

echo "== Escalabilidade fraca (carga por worker constante, lado ∝ √p) =="
executa fraca seq 1 - "$LADO_BASE $LADO_BASE $MAX_ITER_FRACA" ./bin/mandelbrot_seq
for p in "${THREADS[@]}"; do
    lado=$(python3 -c "import math;print(round($LADO_BASE*math.sqrt($p)))")
    executa fraca omp "$p" dynamic "$lado $lado $MAX_ITER_FRACA" \
        env OMP_SCHEDULE=dynamic OMP_NUM_THREADS="$p" ./bin/mandelbrot_omp
done
for p in "${PROCESSOS[@]}"; do
    lado=$(python3 -c "import math;print(round($LADO_BASE*math.sqrt($p)))")
    executa fraca mpi "$p" ciclica "$lado $lado $MAX_ITER_FRACA" \
        env DECOMP=ciclica mpirun --oversubscribe -np "$p" ./bin/mandelbrot_mpi
done

echo
echo "medições em $SAIDA"
echo "== Validação: um único checksum por (experimento, tamanho) =="
python3 - "$SAIDA" <<'CHECK'
import csv, sys
from collections import defaultdict
vistos = defaultdict(set)
with open(sys.argv[1]) as f:
    for l in csv.DictReader(f):
        chave = (l["experimento"], l["largura"] + "x" + l["altura"] + "x" + l["max_iter"])
        vistos[chave].add(l["checksum"])
ruins = {k: v for k, v in vistos.items() if len(v) > 1}
for (exp, tam), cks in sorted(ruins.items()):
    print("  DIVERGENTE: %s %s -> %s" % (exp, tam, sorted(cks)))
if ruins:
    print("FALHA: rode ./scripts/validar.sh para localizar a configuração culpada.")
    sys.exit(1)
print("  ok: %d combinações medidas, um checksum cada." % len(vistos))
CHECK
