# Marco 1 — Paralelização do Conjunto de Mandelbrot

Programação Paralela (CCO085) · IESB 2026/2 · Campus Asa Sul · Turma CCONM3B (noturno) · Prof. Rodrigo Gonçalves · 24/09/2026

## 1. Identificação

**Grupo de dois integrantes.** As três frentes da Seção 3 estão cobertas, com a de MPI
acumulada pelo primeiro integrante:

| Integrante | Matrícula | Frente (Seção 3) |
|---|---|---|
| Gabriel Henrique Kuhn Paz | 2612130027 | Baseline e Perfilamento **+** Versão MPI (memória distribuída) |
| Lara Alves | 2322130053 | Versão OpenMP (memória compartilhada) |

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

## 2. O modelo matemático e o algoritmo

### 2.1 O conjunto de Mandelbrot

Para cada número complexo `c`, considere a família de funções quadráticas
`f_c(z) = z² + c` e a **órbita do zero** sob iteração de `f_c`:

```
z₀ = 0        z₁ = c        z₂ = c² + c       …       z_{n+1} = z_n² + c
```

O conjunto de Mandelbrot é o conjunto dos parâmetros para os quais essa órbita **não diverge**:

```
M = { c ∈ ℂ : a sequência (z_n) permanece limitada }
```

Ele não é definido por uma fórmula fechada, e sim por um critério de comportamento
assintótico — é por isso que só se pode decidir sobre um ponto **iterando**, e é daí que vem
todo o custo computacional do problema.

### 2.2 O critério de escape e o raio 2

O que torna o problema tratável é um resultado clássico: **se em algum momento `|z_n| > 2`,
a órbita necessariamente diverge.** O argumento é curto. Todo `c ∈ M` satisfaz `|c| ≤ 2`;
assim, se `|z| > 2` e `|z| ≥ |c|`, então

```
|z² + c| ≥ |z|² − |c| ≥ |z|² − |z| = |z| · (|z| − 1) > |z|
```

ou seja, o módulo cresce estritamente a cada passo, e o crescimento se acelera — a divergência
é inevitável. Logo o teste `|z| > 2` é uma **condição suficiente de divergência**, não uma
heurística: o raio 2 não é um parâmetro ajustável, é o valor exato que o teorema fornece.

Duas consequências práticas orientam a implementação:

- o código testa `|z|² > 4` em vez de `|z| > 2`, porque elevar ao quadrado evita a raiz
  quadrada e o predicado é logicamente idêntico;
- o teste é **assimétrico**: o escape é demonstrável em tempo finito, mas a permanência não.
  Nenhum número finito de iterações prova que `c ∈ M`.

É essa assimetria que obriga a existência do `max_iter`: ele trunca a decisão. O que o
programa calcula é a **função de tempo de escape**

```
k(c) = min { n ≤ K : |z_n| > 2 },  ou K se não houver escape até K
```

e o conjunto que ele desenha é uma **superaproximação** de `M` — todo ponto classificado
como interior pode ser um ponto exterior de escape lento. Aumentar `K` refina a aproximação e
aumenta o custo proporcionalmente.

### 2.3 Do modelo ao código

Escrevendo `z = x + yi` e `c = a + bi`, a multiplicação complexa se abre em aritmética real:

```
z² + c = (x² − y² + a) + (2xy + b) i
```

que é exatamente o corpo do laço, sem nenhuma biblioteca de números complexos:

```cpp
double tmp = zr * zr - zi * zi + cr;   // parte real
zi         = 2.0 * zr * zi + ci;       // parte imaginária
zr         = tmp;                      // atualização simultânea
```

A variável `tmp` existe porque a atualização é **simultânea**: a nova parte imaginária depende
do `zr` **antigo**. Sobrescrever `zr` antes de calcular `zi` produziria outro sistema
dinâmico. O corpo custa `Θ(1)` — três multiplicações (`zr²`, `zi²`, `zr·zi`; a multiplicação
por 2 é convertida em soma pelo compilador) e quatro adições ou subtrações, reaproveitando
`zr²` e `zi²` entre o teste de escape e a atualização.

O domínio amostrado, `x ∈ [-2, 1]` e `y ∈ [-1.5, 1.5]`, contém `M` inteiro: o conjunto está
contido no disco `|c| ≤ 2`, sua extensão real é `[-2 , 0.25]` e a imaginária não passa de
`±1.13`. A grade é uniforme, com
`c_{i,j} = (x_min + Δx · i/(W−1)) + (y_min + Δy · j/(H−1)) i`.

### 2.4 Complexidade assintótica

Seja `W` a largura, `H` a altura e `K` o `max_iter`. Como o laço de escape de um pixel custa
`O(1)` a `O(K)` com corpo de custo constante:

- **Pior caso:** `Θ(W · H · K)` — atingido se todos os pixels pertencessem a `M`;
- **Caso real:** `Θ(W · H · k̄)`, onde `k̄` é o tempo de escape médio sobre a região
  amostrada. Ele depende do domínio e de `K`, **não** da resolução.

O `checksum` não é só um código de verificação: ele é `Σ k(c)`, ou seja, **o trabalho total
do programa**, e `k̄ = checksum / (W·H)` é uma soma de Riemann que estima a média de `k` sobre
o domínio. Refinar a grade não muda essa média — apenas a estima melhor. Medimos
`k̄ = 172,3`, `172,5` e `172,5` nas três entradas: constante, como o modelo prevê, contra um
`K = 1000`. Confirma-se também a linearidade no número de pixels: quadruplicando `W·H`, o
tempo cresce `4,08×` e depois `3,97×`.

Memória: `W·H` inteiros de 4 bytes (64 MB em 4000×4000), escritos uma vez, sequencialmente.
O acesso é `iteracoes[j·W + i]` com `i` no laço interno, ou seja, percorre a memória na ordem
em que ela está disposta — localidade espacial ótima, sem *cache thrashing*.

### 2.5 O que o modelo impõe à paralelização

Três propriedades matemáticas determinam tudo o que vem nas Seções 6 e 7.

**A órbita é serial; os parâmetros são independentes.** Dentro de um pixel, `z_{n+1}` depende
de `z_n`: é uma cadeia estritamente serial, sem paralelismo em nível de instrução a extrair, e
com número de iterações desconhecido de antemão. Já `k(c₁)` e `k(c₂)` não se comunicam para
`c₁ ≠ c₂`. O problema é *embaraçosamente paralelo* **na dimensão dos parâmetros**, e é aí que
toda a paralelização atua. A única escrita compartilhada é a acumulação do `checksum`.

**`k` é radicalmente não uniforme, e de forma geometricamente estruturada.** Para `c ∈ M`,
`k(c) = K`; para `c` distante, `k(c)` é de poucas unidades. Como `M` é conexo e tem área
positiva concentrada em torno da cardioide principal, os pixels caros **formam uma figura
compacta no miolo do domínio** — não estão espalhados. É esse fato, e não o volume de dados,
que faz do balanceamento de carga o problema central deste projeto.

**`M` é simétrico em relação ao eixo real.** Como `f_c̄(z̄) = conj(f_c(z))`, a órbita de `c̄` é
a conjugada da órbita de `c`, e portanto `k(a + bi) = k(a − bi)`. Com o domínio centrado em
`y = 0`, **qualquer divisão em duas metades horizontais é exatamente equilibrada** — o que
explica, por teorema e não por coincidência, o empate entre as políticas com 2 threads
(Seção 7.1) e o bom desempenho da decomposição em blocos com `np = 2` (Seção 7.2). A simetria
se perde a partir de 4 divisões, e é exatamente aí que o desbalanceamento aparece.

**Consequência numérica.** A fronteira `∂M` é um fractal, e perto dela `k` é extremamente
sensível: uma perturbação de arredondamento muda a contagem de iteração. Isso não é
curiosidade teórica — foi o que observamos ao ver o `checksum` divergir em 4 422 unidades
entre dois compiladores, discutido na Seção 8.

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
trechos explicitamente sequenciais (alocação e acumulação final) e ignora todo o custo
*introduzido* pela paralelização — sincronização, comunicação, desbalanceamento, coerência de
cache. O valor de 909× é artefato dessa contabilidade, não meta.

A utilidade real da estimativa é servir de régua: nossos primeiros resultados com 8 threads
dão **5,82×** contra os **7,94×** previstos por Amdahl. Essa lacuna de 2,12× é exatamente o
objeto de estudo do Marco 2, e a Seção 7 mostra que a maior parte dela tem uma causa já
identificada e medida.

<figure class="grafico">
<img src="resultados/amdahl_vs_medido.png">
<figcaption><strong>Figura 1</strong> — Teto de Amdahl contra o speedup efetivamente medido. Até 2 workers as curvas coincidem; a partir de 4 a lacuna se abre, e é ela que o Marco 2 precisa explicar.</figcaption>
</figure>

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

<figure class="grafico">
<img src="resultados/escalonamento_omp.png">
<figcaption><strong>Figura 2</strong> — Speedup por política de escalonamento. As três curvas são indistinguíveis até 2 threads e divergem a partir de 4.</figcaption>
</figure>

Com 2 threads as três empatam, pela simetria demonstrada na Seção 2.5. A partir de 4 a
diferença explode: `dynamic` entrega **2,17× mais desempenho que `static` no mesmo
hardware**, apenas distribuindo melhor o trabalho. É a confirmação experimental de que o
gargalo é desbalanceamento de carga.

### 7.2 MPI — memória distribuída

Decomposição de domínio por linhas, com **duas variantes selecionáveis em tempo de execução**
(`DECOMP=bloco|ciclica`), para que ambas as curvas saiam da mesma campanha:

- **`bloco`** — faixas contíguas. É a decomposição estática ingênua e, pela concentração
  geométrica de `k` descrita na Seção 2.5, o pior caso possível para este problema. Mantida
  deliberadamente como termo de comparação;
- **`ciclica`** — linhas intercaladas com passo `nprocs`, que distribui as linhas caras entre
  todos os processos.

Operações coletivas: **`MPI_Gatherv`** reconstrói a imagem completa no rank 0 — é a
comunicação real do programa (64 MB em 4000²) e o que viabiliza a validação elemento a
elemento — e **`MPI_Reduce`** combina `checksum` e tempos. Cálculo e comunicação são
cronometrados separadamente, e um campo `desbalanceamento` (razão entre o processo mais lento
e o mais rápido) é reportado a cada execução.

<figure class="largo">
<img src="docs/fig-decomposicao-blocos.jpeg">
<figcaption><strong>Figura 3</strong> — Por que a decomposição em blocos contíguos falha. Com 2 processos a simetria do conjunto em torno de <code>y = 0</code> equilibra as metades; com 4, as duas faixas centrais absorvem a figura inteira e as das pontas ficam ociosas.</figcaption>
</figure>

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

<figure class="grafico">
<img src="resultados/decomposicao_mpi.png">
<figcaption><strong>Figura 4</strong> — As duas decomposições medidas lado a lado. A curva de blocos contíguos <strong>decresce</strong> entre 2 e 4 processos; a cíclica acompanha o ideal.</figcaption>
</figure>

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
validação elemento a elemento, e `./scripts/medir.sh` cobre escalabilidade forte e fraca
gerando CSV, com os gráficos produzidos por `./scripts/graficos.py`.

Pendências até o Marco 2: substituir o baseline provisório pelo código oficial e repetir a
campanha; refazer as medições definitivas na máquina do laboratório; e decompor a lacuna de
2,12× em relação a Amdahl entre desbalanceamento residual, sincronização e limite de banda de
memória.
