# Animação do modelo matemático

Três cenas em [Manim](https://www.manim.community/) que explicam visualmente o que o
projeto faz, na ordem em que a defesa precisa:

| Cena | Responde | Duração |
|---|---|---|
| `Orbita` | Qual é o modelo e que problema matemático ele resolve | ~13 s |
| `TempoEscape` | O que o programa calcula, e por que sequencialmente | ~8 s |
| `Paralelizar` | Por que blocos contíguos falham e a cíclica equilibra | ~9 s |

Vídeos prontos em `videos/`. Para regerar:

```bash
python3 -m venv .venv-manim && .venv-manim/bin/pip install manim importlib_metadata
brew install ffmpeg          # ou o equivalente da sua distribuição
cd animacao && ../.venv-manim/bin/manim -qh --media_dir media mandelbrot.py Orbita TempoEscape Paralelizar
```

## Notas

- Usa `Text` com unicode em vez de `MathTex`, então **não precisa de LaTeX instalado**.
- `Paralelizar` calcula o desbalanceamento a partir da malha real, com o mesmo
  `max_iter = 1000` da campanha de medição. Ele mostra ~35×; a medição em 4000×4000 deu
  41,03×. A diferença é a resolução da malha (200 linhas contra 4000), não o fenômeno.
- A coloração usa escala logarítmica em `k`: em escala linear a maioria dos pontos escapa
  cedo e a imagem satura, escondendo a estrutura.
