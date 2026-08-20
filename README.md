# Mandelbrot Paralelo — Programação Paralela (CCO085, IESB 2026/2)

Projeto acadêmico da disciplina de Programação Paralela: paralelização do
**Conjunto de Mandelbrot** (problema nº 3) em **OpenMP** (memória compartilhada)
e **MPI** (memória distribuída), a partir de um código sequencial de referência.

Integrantes e frentes em [AUTORES.md](AUTORES.md). Proposta em [docs/proposta.md](docs/proposta.md).

> **Atenção:** o código em `src/seq/` é **provisório**, escrito apenas para
> montar e testar o pipeline (compilação, validação, medição, gráficos). Quando
> o professor entregar o código sequencial oficial, ele substitui o provisório e
> passa a definir o gabarito — a partir daí, não se altera a lógica nem a entrada
> dele.

## Estrutura

```
src/seq/      código sequencial (referência / baseline)
src/openmp/   versão OpenMP
src/mpi/      versão MPI
scripts/      validação de corretude, medição (gera CSV) e gráficos
resultados/   CSV de medição e gráficos gerados
docs/         proposta e documentos dos marcos
```

## Ambiente

O ambiente de referência da disciplina é **Linux + g++ + OpenMPI**. No macOS,
use o contêiner Docker:

```bash
docker build -t pp-mandelbrot .
docker run --rm -it -v "$PWD":/projeto pp-mandelbrot
```

Dentro do contêiner (ou no laboratório), tudo funciona igual.

## Compilar

```bash
make            # bin/mandelbrot_seq, bin/mandelbrot_omp, bin/mandelbrot_mpi
```

As três versões são compiladas com **`-ffp-contract=off`**. Isso não é detalhe:
sem a flag, quando `$(CXX)` e o compilador embrulhado pelo `$(MPICXX)` são
diferentes, cada um funde `zr*zr - zi*zi + cr` em FMA de um jeito, pixels na
fronteira de escape trocam de contagem de iteração, e a validação falha **sem que
haja erro de lógica**. É flag de compilação, não alteração da lógica de cálculo.

## Executar

Os três programas recebem `largura altura max_iter` (padrão `2000 2000 1000`) e
imprimem uma linha `key=valor`. Todos aceitam `--dump ARQ`, que grava a matriz de
iterações em binário para a validação.

```bash
./bin/mandelbrot_seq 2000 2000 1000
./bin/mandelbrot_seq 2000 2000 1000 --perfil        # tempo por trecho + Amdahl

OMP_NUM_THREADS=4 OMP_SCHEDULE=dynamic ./bin/mandelbrot_omp 2000 2000 1000

mpirun -np 4 ./bin/mandelbrot_mpi 2000 2000 1000                 # decomposição em blocos
DECOMP=ciclica mpirun -np 4 ./bin/mandelbrot_mpi 2000 2000 1000  # linhas intercaladas
```

O MPI reporta `tempo`, `calculo`, `comunicacao` e `desbalanceamento` (razão entre
o rank mais lento e o mais rápido). Note que o `MPI_Gatherv` é um ponto de
sincronização: com carga desbalanceada, o tempo de espera dos ranks rápidos
aparece dentro de `comunicacao` — por isso o campo `desbalanceamento` existe, para
separar as duas causas.

## Validar corretude

```bash
make validar        # ou ./scripts/validar.sh
```

Compara a matriz de iterações **elemento a elemento** contra o baseline, em todas
as combinações de threads, escalonamentos, processos e decomposições. Não usa
checksum — somas podem colidir. Sai com código != 0 no primeiro desvio.

## Medir e gerar gráficos

```bash
make medir          # scripts/medir.sh + scripts/graficos.py
```

`scripts/medir.sh` gera `resultados/medicoes.csv` com escalabilidade **forte**
(entrada fixa, mais workers) e **fraca** (entrada ∝ √p, carga por worker
constante), varrendo os três escalonamentos de OpenMP e as duas decomposições de
MPI. Protocolo no topo do script: 5 repetições por configuração, 1 execução de
aquecimento descartada, 3 tamanhos de entrada. Ao final, falha se algum tamanho
produzir mais de um checksum.

`scripts/graficos.py` gera em `resultados/`:

| Arquivo | Conteúdo |
|---|---|
| `tempo_{omp,mpi}.png` | tempo de execução por número de workers |
| `speedup_{omp,mpi}.png` | speedup contra a curva ideal |
| `eficiencia_{omp,mpi}.png` | eficiência = speedup / workers |
| `escalonamento_omp.png` | `static` × `dynamic` × `guided` |
| `decomposicao_mpi.png` | blocos contíguos × linhas intercaladas |
| `comunicacao_mpi.png` | fração do tempo gasta em comunicação |
| `escalabilidade_fraca.png` | eficiência fraca por número de workers |

## Perfilar (frente de baseline)

```bash
./bin/mandelbrot_seq 2000 2000 1000 --perfil   # tempo por trecho, fração paralelizável, Amdahl
make perfil && ./bin/mandelbrot_seq_prof 2000 2000 1000 && gprof ./bin/mandelbrot_seq_prof gmon.out | head -40
```

O `--perfil` dá a tabela por trecho do código provisório. Quando o sequencial
oficial chegar, o `gprof` (ou `perf record` no laboratório) dá a granularidade
por função exigida no Marco 1.
