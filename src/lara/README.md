# Mandelbrot: experimentos independentes da pasta `src/lara`

Esta pasta **nao altera** o `Makefile` principal nem os fontes de `src/seq`, `src/mpi` ou `src/openmp`.

## Requisitos
Linux/WSL: `g++`, `make`, OpenMP (GCC) e Open MPI (`mpicxx`, `mpirun`).
No terminal VS Code, estando na raiz `pp-mandelbrot`:

```bash
cd src/lara
make
```

Se ainda nao instalou MPI, pode compilar e testar primeiro apenas `make sequencial openmp`.

## Experimentos: 400 colunas x 600 linhas = 240.000 pixels

```bash
./sequencial 400 600 1000
./openmp 400 600 1000 coordenador 4 16
./openmp 400 600 1000 todos 4 16
mpirun -np 5 ./mpi 400 600 1000 mestre ciclica
mpirun -np 4 ./mpi 400 600 1000 todos ciclica
mpirun -np 3 ./hibrido 400 600 1000 mestre ciclica 2 16
mpirun -np 3 ./hibrido 400 600 1000 todos ciclica 2 16
```

Troque `ciclica` por `bloco` para comparar distribuicao. Troque `16` por `1`, `64` ou `256` para estudar o custo do agendamento dinamico OpenMP.

**Importante:** MPI distribui **linhas estaticamente** (bloco ou ciclica). O OpenMP usa agendamento dinamico de **pixels**. O modelo MPI mestre distribui tarefas inicialmente, mas nao redistribui trabalho a medida que os ranks terminam. Uma fila dinamica MPI seria um experimento adicional.

**Coordenador OpenMP:** a thread 0 nao calcula; as demais pegam lotes usando `atomic fetch_add`. Nesse modo, `collapse` nao e usado, pois o trabalho e gerenciado por indice linear. O modo `todos` usa `collapse(2)` + `schedule(dynamic, chunk)`.

**Medicoes:** `tempo` MPI cobre inicio sincronizado, distribuicao, calculo e coleta. Nao inclui a remontagem final da imagem no rank 0, a impressao nem os `MPI_Reduce` das metricas. `calculo` e o maximo dos tempos locais de calculo; `comunicacao` e o maximo dos tempos locais de comunicacao/espera. **Nao some** `calculo + comunicacao` esperando obter `tempo`, pois os maximos podem ocorrer em ranks diferentes. No OpenMP, `tempo` inclui a criacao da regiao paralela. O checksum e calculado fora da medicao nas versoes locais. O checksum MPI e calculado apos a remontagem. O mesmo checksum em todas as versoes e uma verificacao inicial, nao prova igualdade pixel a pixel.

Para comparar, execute cada configuracao varias vezes, use a mediana, mantenha `largura`, `altura` e `max_iter` identicos, e controle a quantidade de nucleos realmente disponiveis. `speedup=T_seq/T_par` e `eficiencia=speedup/p`, deixando explicito o que conta como recurso `p`. A lei de Amdahl fornece uma previsao teorica dependente da fracao serial; nao se calcula essa fracao apenas com o numero de ranks.

**Limitacao de desempenho:** imagem de 240 mil pixels pode ser pequena para MPI e sofrer com overhead. Vale testar tambem 2000x2000 e 4000x4000.
