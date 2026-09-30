# Animação do projeto

Uma cena única em [Manim](https://www.manim.community/), `Projeto`, que percorre o trabalho
inteiro em três atos — na ordem em que a defesa precisa. Vídeo pronto em
`videos/Projeto.mp4` (~35 s, 1080p).

| Ato | Responde | O que aparece |
|---|---|---|
| 1. O modelo | Qual é o modelo e que problema matemático ele resolve | Órbita do zero no plano complexo, círculo de raio 2, um `c` que fica limitado e outro que escapa. Fecha na assimetria que obriga o `max_iter` |
| 2. O que o programa calcula | Como funciona sequencialmente | `k(c)` colorido, com varredura linha a linha, e o que é caro ou barato |
| 3. Como paralelizamos | Como pensamos em paralelizar | Blocos contíguos × linhas intercaladas, com as barras de trabalho por processo |

## Regerar

```bash
python3 -m venv .venv-manim
.venv-manim/bin/pip install manim importlib_metadata
brew install ffmpeg                      # ou o equivalente da sua distribuição
cd animacao && ../.venv-manim/bin/manim -qh --media_dir media mandelbrot.py Projeto
```

## Notas de implementação

- Usa `Text` com unicode em vez de `MathTex`, então **não exige LaTeX instalado**. Por isso a
  recorrência aparece como `z(n+1) = z(n)² + c`: o subscrito `ₙ` não existe na fonte.
- A coloração é **logarítmica em `k`**. Em escala linear a maioria dos pontos escapa cedo, a
  imagem satura em branco e a estrutura desaparece.
- As barras de trabalho por processo são **calculadas da malha real**, com o mesmo
  `max_iter = 1000` da campanha de medição — não são valores digitados.
- O desbalanceamento exibido fica em torno de 33×; a campanha em 4000×4000 mediu **41,03×**.
  A diferença é a resolução da malha da animação (340 linhas contra 4000), não o fenômeno.
