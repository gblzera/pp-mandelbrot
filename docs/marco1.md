# Marco 1 — Paralelização do Conjunto de Mandelbrot

Programação Paralela (CCO085) · IESB 2026/2 · Campus Asa Sul · Turma CCONM3B (noturno) · Prof. Rodrigo Gonçalves · 24/09/2026

## 1. Identificação

**Grupo de dois integrantes.** As três frentes da Seção 3 estão cobertas, com a de MPI
acumulada pelo primeiro integrante:

| Integrante | Matrícula | Frente (Seção 3) |
|---|---|---|
| Gabriel Henrique Kuhn Paz | 2612130027 | Baseline e Perfilamento **+** Versão MPI (memória distribuída) |
| Lara Alves | — | Versão OpenMP (memória compartilhada) |

O grupo não conseguiu fechar o trio e a possibilidade de entrega em dupla foi consultada
previamente ao professor. A arguição cruzada permanece aplicável: cada integrante pode ser
questionado sobre frente que não conduziu — e, no caso do primeiro integrante, sobre a frente
de OpenMP, que é a única que não é sua.

**Problema nº 3 — Conjunto de Mandelbrot.** Repositório:
`github.com/gblzera/pp-mandelbrot` (privado, acesso concedido ao professor).

> **Ressalva sobre o código de referência.** O código sequencial oficial do problema 3 não
> nos foi entregue até esta data. Toda a análise abaixo é feita sobre uma implementação
> provisória própria (`src/seq/mandelbrot_seq.cpp`), escrita com o único objetivo de montar
> e validar o pipeline de compilação, medição e verificação. Assim que o código oficial for
> disponibilizado, ele substitui o provisório e passa a definir o gabarito; o instrumental
> aqui descrito é independente do kernel e será reaplicado sem alterações.

## 2. O algoritmo sequencial

Para cada ponto `c` de uma grade que cobre a região `x ∈ [-2, 1]`, `y ∈ [-1.5, 1.5]` do plano
complexo, itera-se a recorrência `z ← z² + c` a partir de `z = 0`, contando quantas iterações
são necessárias até `|z|² > 4` (o ponto escapa, está fora do conjunto) ou até atingir
`max_iter` (o ponto é considerado pertencente ao conjunto). A saída é uma matriz
`largura × altura` de contagens de iteração, e o `checksum` — a soma de todas as contagens —
é o critério objetivo de corretude usado no projeto.

### Complexidade assintótica

Seja `W` a largura, `H` a altura e `K` o `max_iter`. O laço de escape de um pixel custa
`O(1)` a `O(K)`, com custo constante por iteração (cinco multiplicações e três somas em ponto
flutuante). Logo:

- **Pior caso:** `Θ(W · H · K)` — atingido se todos os pixels pertencerem ao conjunto;
- **Caso real:** `Θ(W · H · k̄)`, onde `k̄` é o número médio de iterações por pixel, que
  depende da região do plano amostrada e de `K`, **não** da resolução.

O `checksum` mede `k̄` diretamente: `k̄ = checksum / (W·H)`. Nas três entradas medidas,
`k̄ = 172,3`, `172,5` e `172,5` — constante, como previsto. Confirma-se também a linearidade
no número de pixels: quadruplicando `W·H`, o tempo cresce `4,08×` e depois `3,97×`.

Memória: `W·H` inteiros de 4 bytes (64 MB em 4000×4000), escritos uma vez, sequencialmente.
O acesso é `iteracoes[j·W + i]` com `i` no laço interno, ou seja, percorre a memória na ordem
em que ela está disposta — localidade espacial ótima, sem *cache thrashing*.

### Estrutura de dependências

Dentro de um pixel, a recorrência é uma **cadeia estritamente serial**: `z_{n+1}` depende de
`z_n`. Não há paralelismo em nível de instrução a extrair de um pixel, e o número de
iterações não é conhecido de antemão. **Entre pixels, porém, não há dependência alguma:**
cada `c` é independente de todos os outros, e a única escrita compartilhada é a acumulação
do `checksum`. É um problema *embaraçosamente paralelo* na dimensão dos pixels — e é aí que
toda a paralelização vai atuar.

O ponto não trivial é que **o custo por pixel varia em ordens de grandeza**: pontos dentro do
conjunto gastam as `K` iterações completas, pontos distantes escapam em poucas. E os pixels
caros não estão espalhados — concentram-se no miolo da imagem. Isso faz do balanceamento de
carga, e não da comunicação, o problema central deste projeto.

## 3. Metodologia de medição

Todas as medições foram feitas **dentro do contêiner oficial da disciplina**
(`iesb/pp-lab:2026.2`), como exige o `README.md` do ambiente, para que sejam comparáveis
entre os trios.

| Item | Valor |
|---|---|
| Imagem | `iesb/pp-lab:2026.2` — Ubuntu 24.04.4 LTS |
| Compilador | g++ 13.3.0 |
| MPI | Open MPI 4.1.6 |
| Flags | `-O2 -Wall -std=c++17 -ffp-contract=off` |
| Núcleos (`nproc`) | 10 |
| Memória | 7 GB |
| Hospedeiro | Docker Desktop sobre macOS / Apple Silicon (aarch64) |
| Cronômetro | `std::chrono::steady_clock` (seq), `omp_get_wtime` (OpenMP), `MPI_Wtime` (MPI) |
| Repetições | 5 por configuração |
| Aquecimento | 1 execução inicial descartada por configuração |
| Entradas | 1000², 2000² e 4000², sempre com `max_iter = 1000` |

O hospedeiro é ARM com núcleos heterogêneos (*performance* e *efficiency*), o que deprime a
eficiência acima de 4 *workers*; as medições definitivas do Marco 2 serão refeitas na máquina
do laboratório. Tudo é reproduzível com `./scripts/medir.sh`, que grava
`resultados/medicoes.csv` e **falha com código de saída diferente de zero** se alguma
configuração produzir um `checksum` divergente.

## 4. Baseline medido

Tempo do trecho de cálculo, em segundos, sobre 5 repetições após descarte de aquecimento:

| Entrada | Média (s) | Desvio (s) | Desvio rel. | Mínimo (s) | `checksum` | `k̄` (iter/pixel) |
|---|---|---|---|---|---|---|
| 1000 × 1000 | 0,3403 | 0,0008 | 0,2 % | 0,3395 | 172 299 552 | 172,3 |
| 2000 × 2000 | 1,3880 | 0,0396 | 2,9 % | 1,3572 | 689 833 076 | 172,5 |
| 4000 × 4000 | 5,5158 | 0,0258 | 0,5 % | 5,4788 | 2 760 790 145 | 172,5 |

O desvio relativo abaixo de 3 % indica que o protocolo é estável e que cinco repetições
bastam para distinguir os ganhos que serão medidos no Marco 2.

## 5. Perfilamento

Instrumentação por trecho embutida no baseline (`./bin/mandelbrot_seq W H K --perfil`),
medindo alocação do buffer, laço de cálculo e acumulação do `checksum`:

| Trecho | 1000² | 2000² | 4000² |
|---|---|---|---|
| Alocação do buffer | 0,15 % | 0,12 % | 0,03 % |
| **Laço de cálculo `z ← z² + c`** | **99,78 %** | **99,81 %** | **99,89 %** |
| Acumulação do `checksum` | 0,06 % | 0,07 % | 0,08 % |
| Total (s) | 0,3554 | 1,3599 | 5,4615 |

**O hotspot é único e inequívoco:** o laço de escape concentra 99,8 % do tempo, e a fração
cresce com a entrada — a alocação é `O(W·H)` de escrita única, enquanto o cálculo é
`O(W·H·k̄)`. Não há segundo candidato a otimizar: qualquer esforço fora desse laço é
irrelevante. Isso é uma boa notícia para a paralelização, porque o hotspot coincide
exatamente com a parte do programa que não tem dependências entre iterações.

## 6. Fração paralelizável e Lei de Amdahl

Tomando a maior entrada (4000², a mais representativa da carga de trabalho real),
`f = 0,9989` e a fração serial é `1 − f = 0,0011`. Pela Lei de Amdahl,
`S(P) = 1 / ((1−f) + f/P)`:

| `P` | Speedup previsto | Eficiência prevista |
|---|---|---|
| 2 | 2,00× | 100 % |
| 4 | 3,99× | 100 % |
| 8 | 7,94× | 99 % |
| 10 | 9,90× | 99 % |
| → ∞ | 909× | — |

**Estes números são um teto, não uma previsão.** A fração serial medida contabiliza apenas os
trechos explicitamente sequenciais (alocação e acumulação final); ela ignora todo o custo
*introduzido* pela paralelização — sincronização, comunicação, desbalanceamento de carga,
tráfego de coerência de cache. O valor de 909× no limite é um artefato dessa contabilidade e
não deve ser lido como meta.

A utilidade real da estimativa é servir de régua: nossos primeiros resultados com 8 threads
dão **5,82×** contra os **7,94×** previstos por Amdahl. Essa lacuna de 2,12× é exatamente o
objeto de estudo do Marco 2, e a Seção 7 mostra que a maior parte dela tem uma causa já
identificada e medida.

## 7. Plano de paralelização

Ambas as frentes atacam o mesmo hotspot da mesma forma — distribuindo **linhas da imagem**
entre os *workers* — porque a independência entre pixels torna essa a decomposição natural, e
uma linha é grande o bastante para amortizar o custo de agendá-la.

### 7.1 OpenMP — memória compartilhada

`#pragma omp parallel for` sobre o laço externo (linhas), com:

- **`schedule(runtime)`**, para que a política venha de `OMP_SCHEDULE` e as três alternativas
  sejam comparadas sem recompilar. Como o custo por linha é fortemente desigual (Seção 2), é
  aqui que está o ganho;
- **`reduction(+:checksum)`** para a condição de corrida na acumulação. Escolhido sobre
  `critical`, que serializaria a região inteira, e sobre `atomic`, que faria uma operação
  atômica por pixel e geraria tráfego de coerência a cada iteração. O `reduction` dá a cada
  thread uma cópia privada e combina uma única vez ao final, o que também elimina *false
  sharing* no acumulador.

Resultados preliminares em 4000², speedup contra o baseline:

| Política | 2 threads | 4 threads | 8 threads |
|---|---|---|---|
| `static` | 1,88× | 1,92× | 2,68× |
| `guided` | 1,88× | 2,16× | 3,92× |
| **`dynamic`** | 1,88× | **3,62×** | **5,82×** |

Com 2 threads as três empatam — o conjunto é simétrico em torno de `y = 0`, então qualquer
corte em duas metades é equilibrado por construção. A partir de 4 a diferença explode:
`dynamic` entrega **2,17× mais desempenho que `static` no mesmo hardware**, apenas
distribuindo melhor o trabalho. É a confirmação experimental de que o gargalo é
desbalanceamento de carga.

### 7.2 MPI — memória distribuída

Decomposição de domínio por linhas, com **duas variantes selecionáveis em tempo de execução**
(`DECOMP=bloco|ciclica`), para que ambas as curvas saiam da mesma campanha:

- **`bloco`** — faixas contíguas. É a decomposição estática ingênua e, para o Mandelbrot, o
  pior caso possível: as linhas caras concentram-se no meio da imagem e o processo do meio
  vira o gargalo. Mantida deliberadamente como termo de comparação;
- **`ciclica`** — linhas intercaladas com passo `nprocs`, que distribui as linhas caras entre
  todos os processos.

Operações coletivas: **`MPI_Gatherv`** reconstrói a imagem completa no rank 0 — é a
comunicação real do programa (64 MB em 4000²) e o que viabiliza a validação elemento a
elemento — e **`MPI_Reduce`** combina `checksum` e tempos. Cálculo e comunicação são
cronometrados separadamente, e um campo `desbalanceamento` (razão entre o processo mais lento
e o mais rápido) é reportado a cada execução.

Resultados preliminares em 4000²:

| Decomposição | `np` | Tempo (s) | Speedup | Eficiência | Desbalanceamento | Comunicação |
|---|---|---|---|---|---|---|
| bloco | 2 | 2,949 | 1,87× | 94 % | 1,00× | 14 ms |
| bloco | 4 | 3,164 | 1,74× | 44 % | **41,03×** | **3 087 ms** |
| cíclica | 2 | 2,983 | 1,85× | 92 % | 1,00× | 13 ms |
| **cíclica** | **4** | **1,541** | **3,58×** | **89 %** | **1,00×** | **16 ms** |

O caso `bloco` com `np=4` é o resultado mais instrutivo do trabalho até aqui: **o speedup cai
ao adicionar processos** (1,87× com 2, 1,74× com 4), assinatura inequívoca de
desbalanceamento. Um processo executa 41 vezes o trabalho do mais rápido. E os 3 087 ms
atribuídos a "comunicação" não são transferência — o volume de dados é idêntico ao da variante
cíclica, que gasta 16 ms. São os processos rápidos **ociosos, bloqueados** no `MPI_Gatherv`,
que é um ponto de sincronização. O campo `desbalanceamento` existe precisamente para separar
espera de transferência; sem ele, atribuiríamos à rede um custo que é de distribuição de
carga.

## 8. Reprodutibilidade e corretude

**Corretude.** `./scripts/validar.sh` compara a matriz de iterações **elemento a elemento**
contra o baseline, em todas as combinações de threads, políticas de escalonamento, processos e
decomposições — 20 configurações — e falha no primeiro desvio. Não usamos apenas `checksum`
porque somas podem colidir; o enunciado pede prova de resultado idêntico, não evidência.

**Reprodutibilidade numérica.** As três versões são compiladas com **`-ffp-contract=off`**.
Sem essa flag, quando `$(CXX)` e o compilador embrulhado pelo `$(MPICXX)` diferem, cada um
funde `zr*zr - zi*zi + cr` em FMA de forma distinta; pixels na fronteira de escape trocam de
contagem de iteração e a validação falha **sem que haja erro de lógica**. Detectamos isso na
prática (divergência de 4 422 unidades no `checksum`) antes de diagnosticar a causa. É flag
de compilação, não alteração da lógica de cálculo, e portanto não conflita com a Seção 10 das
orientações. Custo medido: cerca de 8,6 % de tempo, aplicado igualmente às três versões, de
modo que as razões de speedup permanecem válidas.

## 9. Situação e próximos passos

Já funcionando: as três versões compilam com `make` puro no ambiente oficial, passam na
validação elemento a elemento, e a campanha de medição (`./scripts/medir.sh`) cobre
escalabilidade forte e fraca gerando CSV, com os gráficos produzidos por
`./scripts/graficos.py`.

Pendências até o Marco 2: substituir o baseline provisório pelo código oficial e repetir toda
a campanha; refazer as medições definitivas na máquina do laboratório; e aprofundar a
discussão do afastamento em relação a Amdahl, decompondo a lacuna de 2,12× entre
desbalanceamento residual, sincronização e limite de banda de memória.
