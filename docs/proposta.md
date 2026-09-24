# Proposta de Projeto — Conjunto de Mandelbrot

**Disciplina:** Programação Paralela (CCO085) — 2026/2
**Curso:** Ciência da Computação — Centro Universitário IESB, Campus Asa Sul
**Professor:** Rodrigo Gonçalves
**Turma:** CCONM3B (noturno)

## Integrantes e frentes

| Integrante | Frente (Seção 3 das orientações) |
|---|---|
| Gabriel Henrique Kuhn Paz — mat. 2612130027 | Baseline e Perfilamento + Versão MPI |
| Lara Alves — mat. 2322130053 | Versão OpenMP |

*Grupo de dois integrantes. O trio não fechou e a entrega em dupla foi consultada
previamente ao professor; as três frentes estão cobertas, com a de MPI acumulada
pelo primeiro integrante.*

## Problema escolhido

**Nº 3 — Conjunto de Mandelbrot.**

## Justificativa da escolha

1. **Paralelismo natural, análise rica.** Cada pixel é calculado de forma
   independente, mas o custo por pixel varia drasticamente: pontos dentro do
   conjunto consomem `max_iter` iterações, enquanto pontos externos escapam em
   poucas. Esse **desbalanceamento natural de carga** é exatamente o que torna
   o estudo comparativo das políticas de escalonamento (`static`, `dynamic`,
   `guided`) exigido na frente OpenMP significativo, e não apenas formal.
2. **Decomposição de domínio clara para MPI.** A divisão da imagem em blocos
   de linhas por processo é direta de implementar e de explicar, com operações
   coletivas naturais (`MPI_Reduce` para o checksum de validação, `MPI_Gatherv`
   para reunir a imagem completa no processo 0) — e o desbalanceamento entre
   faixas gera discussão real de overhead e de decomposição alternativa.
3. **Demonstração ao vivo verificável.** O resultado é visual e o critério de
   corretude é objetivo: a matriz de contagens de iteração das versões
   paralelas deve ser idêntica à do baseline, para qualquer número de
   threads/processos. Implementado em `scripts/validar.sh`, que compara as
   matrizes elemento a elemento e falha com código de saída != 0.

## Nota sobre reprodutibilidade numérica

As três versões são compiladas com `-ffp-contract=off`. Sem essa flag, quando
`$(CXX)` e o compilador embrulhado pelo `$(MPICXX)` diferem, a expressão
`zr*zr - zi*zi + cr` é fundida em FMA de formas distintas e pixels na fronteira
de escape trocam de contagem de iteração — a validação de corretude falha sem que
haja erro de lógica. É flag de compilação, não alteração da lógica de cálculo, e
portanto não conflita com a Seção 10 das orientações.

## Plano de trabalho

### Frente 1 — Baseline e Perfilamento
- Análise do código sequencial de referência: complexidade O(largura × altura
  × max_iter) no pior caso, com custo real dependente da região do plano;
- Perfilamento com tabela de tempo por trecho, evidenciando o hotspot esperado
  (laço de iteração z ← z² + c);
- Protocolo de medição: ≥3 tamanhos de entrada, 5 repetições por configuração
  com descarte de aquecimento, máquina e flags documentadas;
- Estimativa da fração paralelizável e speedup máximo pela Lei de Amdahl.

### Frente 2 — Versão OpenMP
- `#pragma omp parallel for` no laço externo (linhas da imagem);
- Tratamento da condição de corrida na acumulação do checksum com `reduction`,
  com justificativa comparativa frente a `critical` e `atomic`;
- Estudo comparativo `static` × `dynamic` × `guided` (via `schedule(runtime)`
  e `OMP_SCHEDULE`), motivado pelo desbalanceamento de carga do problema;
- Curva de speedup por número de threads (1, 2, 4, 8), validada contra o
  baseline.

### Frente 3 — Versão MPI
- Decomposição de domínio por blocos de linhas entre os processos;
- Operações coletivas: `MPI_Gatherv` (reconstrução da imagem no rank 0, que é a
  comunicação real do programa) e `MPI_Reduce` (checksum e tempos);
- **Comparação de duas decomposições na mesma campanha**: blocos contíguos
  (estática ingênua) × linhas intercaladas (`DECOMP=ciclica`), selecionáveis em
  tempo de execução. A primeira é o pior caso para o Mandelbrot e serve de termo
  de comparação;
- Análise do overhead de comunicação em função do número de processos, com
  cálculo e comunicação cronometrados separadamente;
- Curva de speedup por número de processos (`-np` 1, 2, 4), validada contra o
  baseline.

### Análise experimental (transversal)
- Gráficos de tempo, speedup e eficiência; escalabilidade forte e fraca;
- Confronto do speedup real com o previsto por Amdahl, discutindo overhead de
  comunicação, desbalanceamento de carga e limite de banda de memória.

## Cronograma

| Período       | Atividade                                                        |
|---------------|------------------------------------------------------------------|
| até 27/08     | Confirmação do problema e do grupo com o professor               |
| 28/08 – 09/09 | Análise do código de referência, perfilamento, baseline, Amdahl  |
| **10/09**     | **Marco 1** — PDF (≤6 págs.) + código                            |
| set – out     | Implementação e refinamento das versões OpenMP e MPI             |
| out – nov     | Campanha de medições, gráficos e análise experimental            |
| **12/11**     | **Marco 2** — versões funcionando + validação + análise          |
| 19 ou 26/11   | Seminário técnico: demonstração ao vivo + arguição               |

## Ambiente e entrega

Desenvolvimento no ambiente de referência da disciplina (Linux, g++, OpenMPI),
replicado localmente via contêiner Docker. Entrega em repositório Git com as
três versões em diretórios separados, Makefile único, script de medição que
gera CSV, gráficos, README e AUTORES.md, com histórico de commits distribuído
ao longo do desenvolvimento.
