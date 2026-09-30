# Marco 1 — Paralelização do Conjunto de Mandelbrot

Programação Paralela (CCO085) · IESB 2026/2 · Campus Asa Sul · Turma CCONM3B (noturno) · Prof. Rodrigo Gonçalves · 30/09/2026

## 1. Identificação

| Integrante | Matrícula | Frente (Seção 3) |
|---|---|---|
| Gabriel Henrique Kuhn Paz | 2612130027 | Baseline e Perfilamento **+** MPI (memória distribuída) |
| Lara Alves | 2322130053 | OpenMP (memória compartilhada) |

**Problema nº 3 — Conjunto de Mandelbrot.** Grupo de dois integrantes; o trio não fechou e a
entrega em dupla foi consultada previamente ao professor. As três frentes estão cobertas.
Repositório: `github.com/gblzera/pp-mandelbrot` (privado, com acesso ao professor).

> **Ressalva.** O código sequencial oficial do problema 3 não nos foi entregue até esta data.
> A análise é feita sobre uma implementação provisória própria (`src/seq/mandelbrot_seq.cpp`),
> escrita para montar e validar o pipeline. Quando o oficial chegar, ele substitui o
> provisório e define o gabarito; o instrumental descrito aqui independe do kernel.

## 2. O modelo matemático

**A pergunta.** Dado um sistema dinâmico `z ← z² + c`, para quais valores do parâmetro `c` a
órbita que começa em `0` **não escapa para o infinito**? É uma pergunta de estabilidade sob
variação de parâmetro — a mesma forma de problema que aparece em diagramas de bifurcação e
bacias de atração.

**A definição.** A órbita do zero é `z₀ = 0`, `z₁ = c`, `z₂ = c² + c`, …, `z_{n+1} = z_n² + c`.

> `M = { c ∈ ℂ : a sequência (z_n) permanece limitada }`

Não há fórmula fechada. `M` é definido por comportamento assintótico, então **só se decide
iterando** — e é daí que vem todo o custo computacional.

### 2.1 O teorema do raio 2

O que torna o problema tratável: **se `|z_n| > 2` em algum momento, a órbita diverge.**
Como todo `c ∈ M` satisfaz `|c| ≤ 2`, se `|z| > 2` e `|z| ≥ |c|`:

```
|z² + c| ≥ |z|² − |c| ≥ |z|² − |z| = |z| · (|z| − 1) > |z|
```

O módulo cresce estritamente e o crescimento acelera. Logo o teste é **condição suficiente de
divergência**, não heurística: o raio 2 é o valor que o teorema fornece, não um ajuste.

| No modelo | No código | Por quê |
|---|---|---|
| `\|z\| > 2` | `zr*zr + zi*zi > 4.0` | elevar ao quadrado evita a raiz; predicado idêntico |
| `z² + c` | `(x²−y²+a) + (2xy+b)i` | multiplicação complexa aberta em aritmética real |
| órbita de `0` | `zr = zi = 0.0` | todo pixel começa no mesmo ponto |

### 2.2 A assimetria que obriga o `max_iter`

- **Escape** é demonstrável em tempo finito — basta uma iteração cruzar o raio 2.
- **Permanência** não é. Nenhum número finito de iterações prova que `c ∈ M`.

Por isso o programa trunca a decisão em `K = max_iter` e calcula a **função de tempo de
escape**:

> `k(c) = min { n ≤ K : |z_n| > 2 }`, ou `K` se não houver escape até `K`

O conjunto desenhado é uma **superaproximação** de `M`: todo ponto classificado como interior
pode ser um ponto exterior de escape lento. Aumentar `K` refina e encarece proporcionalmente.

## 3. O algoritmo sequencial

Três laços encaixados, sem biblioteca de números complexos:

```cpp
for (int j = 0; j < altura; j++)                    // linha da imagem
  for (int i = 0; i < largura; i++) {               // coluna
    double zr = 0.0, zi = 0.0; int iter = 0;
    while (zr*zr + zi*zi <= 4.0 && iter < max_iter) {   // <- 99,8% do tempo
      double tmp = zr*zr - zi*zi + cr;               // parte real
      zi         = 2.0*zr*zi + ci;                   // parte imaginária
      zr         = tmp;                              // atualização simultânea
      iter++;
    }
    iteracoes[j*largura + i] = iter;                 // k(c)
  }
```

O `tmp` existe porque a atualização é **simultânea**: a nova parte imaginária usa o `zr`
antigo. Sobrescrever antes produziria outro sistema dinâmico.

**Domínio amostrado:** `x ∈ [-2, 1]`, `y ∈ [-1.5, 1.5]` — contém `M` inteiro (extensão real
`[-2 , 0.25]`, imaginária até `±1.13`). Grade uniforme.

### Complexidade

| | Custo | Observação |
|---|---|---|
| Corpo do laço `while` | `Θ(1)` | 3 multiplicações + 4 somas; `×2` vira soma no compilador |
| Um pixel | `O(1)` a `O(K)` | depende de onde `c` cai |
| **Pior caso** | `Θ(W · H · K)` | se todos os pixels pertencessem a `M` |
| **Caso real** | `Θ(W · H · k̄)` | `k̄` = tempo de escape médio |
| Memória | `W·H` × 4 bytes | 64 MB em 4000²; escrita sequencial, localidade ótima |

O `checksum` não é só verificação: ele é `Σ k(c)`, ou seja **o trabalho total**. E
`k̄ = checksum/(W·H)` é uma soma de Riemann que estima a média de `k` sobre o domínio — por
isso **não depende da resolução**. Medimos `172,3`, `172,5` e `172,5` contra `K = 1000`.

## 4. Metodologia, baseline e perfilamento

Tudo medido **dentro do contêiner oficial da disciplina**, como exige o `README.md` do
ambiente, para que os resultados sejam comparáveis entre os grupos.

| Ambiente | | Protocolo | |
|---|---|---|---|
| Imagem | `iesb/pp-lab:2026.2` (Ubuntu 24.04.4) | Repetições | 5 por configuração |
| Compilador | g++ 13.3.0 | Aquecimento | 1 execução descartada |
| MPI | Open MPI 4.1.6 | Entradas | 1000², 2000², 4000² |
| Flags | `-O2 -Wall -std=c++17 -ffp-contract=off` | `max_iter` | 1000 |
| `nproc` / memória | 10 núcleos / 7 GB | Cronômetro | `steady_clock`, `omp_get_wtime`, `MPI_Wtime` |
| Hospedeiro | Docker sobre macOS / Apple Silicon (aarch64) | Reprodução | `./scripts/medir.sh` |

O hospedeiro é ARM com núcleos heterogêneos, o que deprime a eficiência acima de 4 *workers*;
as medições definitivas do Marco 2 serão refeitas no laboratório. O script **falha com código
diferente de zero** se alguma configuração produzir `checksum` divergente.

**Baseline** — tempo do trecho de cálculo, 5 repetições após descarte:

| Entrada | Média (s) | Desvio (s) | Desvio rel. | Mínimo (s) | `checksum` | `k̄` |
|---|---|---|---|---|---|---|
| 1000 × 1000 | 0,3403 | 0,0008 | 0,2 % | 0,3395 | 172 299 552 | 172,3 |
| 2000 × 2000 | 1,3880 | 0,0396 | 2,9 % | 1,3572 | 689 833 076 | 172,5 |
| 4000 × 4000 | 5,5158 | 0,0258 | 0,5 % | 5,4788 | 2 760 790 145 | 172,5 |

Desvio relativo abaixo de 3 % — cinco repetições bastam. Quadruplicando `W·H`, o tempo cresce
`4,08×` e depois `3,97×`: linearidade no número de pixels, como o modelo prevê.

**Perfilamento** — instrumentação por trecho (`./bin/mandelbrot_seq W H K --perfil`):

| Trecho | 1000² | 2000² | 4000² |
|---|---|---|---|
| Alocação do buffer | 0,15 % | 0,12 % | 0,03 % |
| **Laço de escape `z ← z² + c`** | **99,78 %** | **99,81 %** | **99,89 %** |
| Acumulação do `checksum` | 0,06 % | 0,07 % | 0,08 % |

**Hotspot único e inequívoco.** A fração cresce com a entrada, porque a alocação é `O(W·H)` e
o cálculo é `O(W·H·k̄)`. Não há segundo candidato — e o hotspot coincide exatamente com a
parte que **não tem dependências entre iterações**.

## 5. Fração paralelizável e Lei de Amdahl

Com `f = 0,9989` em 4000² e `S(P) = 1 / ((1−f) + f/P)`:

| `P` | 2 | 4 | 8 | 10 | → ∞ |
|---|---|---|---|---|---|
| **Speedup previsto** | 2,00× | 3,99× | 7,94× | 9,90× | 909× |
| **Medido (OpenMP `dynamic`)** | 1,88× | 3,62× | 5,82× | — | — |

**Teto, não previsão.** A fração serial medida só conta o que é explicitamente sequencial
(alocação e acumulação) e ignora o custo *introduzido* pela paralelização — sincronização,
comunicação, desbalanceamento, coerência de cache. O `909×` é artefato dessa contabilidade.

A régua útil é Amdahl no `P` real: **7,94× previstos contra 5,82× medidos**. Essa lacuna de
**2,12×** é o objeto do Marco 2, e a Seção 6 mostra que ela tem causa identificada e medida.

<figure class="grafico">
<img src="resultados/amdahl_vs_medido.png">
<figcaption><strong>Figura 1</strong> — Até 2 workers as curvas coincidem; a partir de 4 a lacuna se abre.</figcaption>
</figure>

## 6. Plano de paralelização

Três propriedades do modelo determinam todas as decisões:

| Propriedade matemática | Consequência para a paralelização |
|---|---|
| A órbita é uma cadeia serial: `z_{n+1}` depende de `z_n` | **Não** se paraleliza dentro de um pixel. Nem o hardware consegue |
| `k(c₁)` e `k(c₂)` não se comunicam | Embaraçosamente paralelo **entre** pixels — é aí que atuamos |
| `k(c) = K` dentro de `M`, pequeno fora; `M` é conexo e compacto | Os pixels caros **formam uma figura no miolo**. Desbalanceamento é o gargalo, não comunicação |
| `f_c̄(z̄) = conj(f_c(z))` ⟹ `k(a+bi) = k(a−bi)` | `M` é simétrico no eixo real: **qualquer divisão em 2 metades é exatamente equilibrada**. A simetria se perde a partir de 4 |

A última linha é teorema, não coincidência — e explica os empates com 2 *workers* abaixo.

### 6.1 OpenMP — memória compartilhada

`#pragma omp parallel for` sobre o laço externo (linhas). Duas decisões:

- **`schedule(runtime)`** — a política vem de `OMP_SCHEDULE`, permitindo comparar as três sem
  recompilar. Como o custo por linha é desigual, é aqui que está o ganho.
- **`reduction(+:checksum)`** — contra `critical`, que serializaria a região inteira, e contra
  `atomic`, que faria uma operação atômica por pixel com tráfego de coerência a cada iteração.
  O `reduction` dá cópia privada por thread e combina uma vez só, o que também elimina *false
  sharing* no acumulador.

| Política | 2 threads | 4 threads | 8 threads |
|---|---|---|---|
| `static` | 1,88× | 1,92× | 2,68× |
| `guided` | 1,88× | 2,16× | 3,92× |
| **`dynamic`** | 1,88× | **3,62×** | **5,82×** |

Empate com 2 (simetria); a partir de 4, `dynamic` entrega **2,17× mais que `static` no mesmo
hardware**, só distribuindo melhor.

<figure class="grafico">
<img src="resultados/escalonamento_omp.png">
<figcaption><strong>Figura 2</strong> — As três curvas são indistinguíveis até 2 threads e divergem a partir de 4.</figcaption>
</figure>

### 6.2 MPI — memória distribuída

Decomposição por linhas, com **duas variantes selecionáveis em execução** (`DECOMP=bloco|ciclica`):

- **`bloco`** — faixas contíguas. Pior caso possível aqui, pela concentração geométrica de
  `k`. Mantida de propósito como termo de comparação.
- **`ciclica`** — linhas intercaladas com passo `nprocs`, distribuindo as caras entre todos.

**Coletivas:** `MPI_Gatherv` reconstrói a imagem no rank 0 — é a comunicação real (64 MB em
4000²) e o que viabiliza a validação elemento a elemento; `MPI_Reduce` combina `checksum` e
tempos. Cálculo e comunicação são cronometrados **separadamente**, e um campo
`desbalanceamento` (rank mais lento ÷ mais rápido) é reportado a cada execução.

<figure class="largo">
<img src="docs/fig-decomposicao-blocos.jpeg">
<figcaption><strong>Figura 3</strong> — Com 2 processos a simetria equilibra as metades; com 4, as faixas centrais absorvem a figura e as das pontas ficam ociosas.</figcaption>
</figure>

| Decomposição | `np` | Tempo (s) | Speedup | Eficiência | Desbalanceamento | Comunicação |
|---|---|---|---|---|---|---|
| bloco | 2 | 2,949 | 1,87× | 94 % | 1,00× | 14 ms |
| bloco | 4 | 3,164 | **1,74×** | 44 % | **41,03×** | **3 087 ms** |
| cíclica | 2 | 2,983 | 1,85× | 92 % | 1,00× | 13 ms |
| **cíclica** | **4** | **1,541** | **3,58×** | **89 %** | **1,00×** | **16 ms** |

**O resultado mais instrutivo do trabalho:** com blocos, o speedup **cai** ao adicionar
processos (1,87× → 1,74×) — assinatura inequívoca de desbalanceamento. Um rank executa 41
vezes o trabalho do mais rápido.

E os **3 087 ms de "comunicação" não são transferência**: o volume é idêntico ao da cíclica,
que gasta 16 ms. São os processos rápidos **bloqueados** no `MPI_Gatherv`, que é ponto de
sincronização. O campo `desbalanceamento` existe para separar espera de transferência — sem
ele, atribuiríamos à rede um custo que é de distribuição de carga.

## 7. Corretude, reprodutibilidade e situação

- **Corretude.** `./scripts/validar.sh` compara a matriz de iterações **elemento a elemento**
  contra o baseline em 20 configurações e falha no primeiro desvio. Checksum sozinho não
  basta: somas podem colidir, e o enunciado pede prova de resultado idêntico.
- **Reprodutibilidade numérica.** As três versões usam `-ffp-contract=off`. Sem a flag,
  quando `$(CXX)` e o compilador do `$(MPICXX)` diferem, cada um funde `zr*zr - zi*zi + cr`
  em FMA de forma distinta. Como `∂M` é fractal e `k` é hipersensível perto dela, pixels de
  borda trocam de contagem: observamos **4 422 unidades** de divergência no `checksum` sem
  erro de lógica. É flag de compilação, não alteração da lógica, e custa ~8,6 % — igual para
  as três versões, então as razões de speedup permanecem válidas.
- **Já funcionando.** As três versões compilam com `make` puro no ambiente oficial, passam na
  validação, e `./scripts/medir.sh` cobre escalabilidade forte e fraca gerando CSV, com
  gráficos por `./scripts/graficos.py`.
- **Material de apoio.** `animacao/mandelbrot.py` gera, com a biblioteca Manim, três cenas
  que animam o modelo: a órbita e o critério de escape, o cálculo de `k(c)` pixel a pixel, e
  a comparação entre as duas decomposições.
- **Pendências até o Marco 2.** Substituir o baseline provisório pelo código oficial e
  repetir a campanha; refazer as medições no laboratório; decompor a lacuna de 2,12× entre
  desbalanceamento residual, sincronização e limite de banda de memória.
