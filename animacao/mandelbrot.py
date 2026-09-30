"""Animação única do projeto: do modelo matemático ao paralelismo.

Uma cena contínua em três atos:
  1. O modelo      — a órbita do zero, o raio de escape 2, e por que existe max_iter
  2. O sequencial  — o que o programa calcula: k(c), linha após linha
  3. O paralelismo — por que blocos contíguos falham e linhas intercaladas equilibram

Sem LaTeX: usa Text com unicode, então roda em máquina sem distribuição TeX.
Render:  manim -qh --media_dir media mandelbrot.py Projeto
"""
import numpy as np
from manim import *

AZUL, VERDE, VERM, AMAR = "#3B7DD8", "#2FA84F", "#D1495B", "#E8A33D"
CINZA = "#9AA0A6"
R_ESCAPE = 2.0
MAX_ITER = 1000          # o mesmo da campanha de medição
CORES_PROC = [AZUL, VERDE, AMAR, VERM]

PALETA = np.array([[255, 247, 214], [245, 158, 66], [150, 40, 90], [30, 45, 120]]) / 255.0


def escape(c, K):
    """Tempo de escape k(c): itera z <- z^2 + c e devolve (k, órbita)."""
    z, orb = 0j, [0j]
    for n in range(1, K + 1):
        z = z * z + c
        orb.append(z)
        if abs(z) > R_ESCAPE:
            return n, orb
    return K, orb


def malha(w, h, K, xr=(-2.0, 1.0), yr=(-1.5, 1.5)):
    """Matriz de tempos de escape — é exatamente o que o baseline calcula."""
    x = np.linspace(*xr, w)
    y = np.linspace(*yr, h)
    c = x[None, :] + 1j * y[:, None]
    z = np.zeros_like(c)
    k = np.zeros(c.shape, dtype=int)
    vivo = np.ones(c.shape, dtype=bool)
    for n in range(K):
        z[vivo] = z[vivo] ** 2 + c[vivo]
        fugiu = vivo & (np.abs(z) > R_ESCAPE)
        k[fugiu] = n + 1
        vivo &= ~fugiu
    k[vivo] = K
    return k


def colorir(k, K):
    """k -> RGB. Preto = pertence ao conjunto (caro). Claro = escapa rápido.

    Escala logarítmica: a maioria dos pontos escapa em poucas iterações, e em
    escala linear a imagem satura em branco e esconde a estrutura.
    """
    dentro = k >= K
    t = np.log1p(k) / np.log1p(K)
    idx = np.clip(t, 0, 1) * (len(PALETA) - 1)
    i0 = np.clip(np.floor(idx), 0, len(PALETA) - 2).astype(int)
    f = (idx - i0)[..., None]
    rgb = PALETA[i0] * (1 - f) + PALETA[i0 + 1] * f
    rgb[dentro] = 0.02
    return (rgb * 255).astype(np.uint8)


class Projeto(Scene):
    def construct(self):
        self.titulo = Text("", font_size=38, weight=BOLD).to_edge(UP, buff=0.35)
        self.add(self.titulo)
        self.ato1_modelo()
        self.ato2_sequencial()
        self.ato3_paralelismo()

    def trocar_titulo(self, texto, cor=WHITE):
        novo = Text(texto, font_size=38, weight=BOLD, color=cor).to_edge(UP, buff=0.35)
        self.play(Transform(self.titulo, novo), run_time=0.7)

    # ------------------------------------------------------------------ ato 1
    def ato1_modelo(self):
        self.trocar_titulo("1. O modelo")

        regra = Text("z(n+1) = z(n)² + c,   começando em z(0) = 0",
                     font_size=28, color=AZUL).next_to(self.titulo, DOWN, buff=0.16)
        pergunta = Text("Para quais c a órbita NÃO escapa para o infinito?",
                        font_size=24, color=CINZA).next_to(regra, DOWN, buff=0.12)
        self.play(FadeIn(regra, shift=UP * 0.15), run_time=0.7)
        self.play(FadeIn(pergunta), run_time=0.6)

        plano = ComplexPlane(
            x_range=[-2.5, 2.5, 1], y_range=[-1.8, 1.8, 1],
            background_line_style={"stroke_opacity": 0.22},
        ).scale(0.95).shift(DOWN * 0.85)
        raio = plano.n2p(2)[0] - plano.n2p(0)[0]
        disco = Circle(radius=raio, color=VERM, stroke_width=3).move_to(plano.n2p(0))
        marca = Text("|z| = 2", font_size=21, color=VERM)
        marca.move_to(plano.n2p(0) + UP * raio * 0.72 + RIGHT * raio * 0.72)
        self.play(Create(plano), run_time=0.9)
        self.play(Create(disco), FadeIn(marca), run_time=0.7)

        legenda = Text("", font_size=25).to_edge(DOWN, buff=0.35)
        self.add(legenda)

        for c, cor, txt in [
            (-0.5 + 0.55j, VERDE, "c = −0,5 + 0,55i   órbita limitada   →   c ∈ M"),
            (0.36 + 0.36j, VERM, "c = 0,36 + 0,36i   escapou   →   c ∉ M"),
        ]:
            _, orb = escape(c, K=30)
            pc = Dot(plano.n2p(c), color=cor, radius=0.07)
            rot = Text("c", font_size=22, color=cor).next_to(pc, UR, buff=0.04)
            self.play(FadeIn(pc), FadeIn(rot),
                      Transform(legenda, Text(txt, font_size=25, color=cor)
                                .to_edge(DOWN, buff=0.35)), run_time=0.6)
            trilha = VGroup()
            for i in range(1, min(len(orb), 15)):
                a, b = orb[i - 1], orb[i]
                if abs(b) > 3.0:
                    break
                trilha.add(Line(plano.n2p(a), plano.n2p(b), color=cor,
                                stroke_width=2.5, stroke_opacity=0.7),
                           Dot(plano.n2p(b), color=cor, radius=0.042))
                self.play(Create(trilha[-2]), FadeIn(trilha[-1]), run_time=0.12)
            self.wait(0.45)
            self.play(FadeOut(trilha), FadeOut(pc), FadeOut(rot), run_time=0.35)

        fecho = VGroup(
            Text("Escape se prova em tempo finito.", font_size=24, color=VERM),
            Text("Permanência, não — por isso existe o max_iter.", font_size=24, color=VERDE),
        ).arrange(DOWN, buff=0.12).to_edge(DOWN, buff=0.3)
        self.play(FadeOut(legenda), FadeIn(fecho), run_time=0.7)
        self.wait(1.5)
        self.play(FadeOut(plano), FadeOut(disco), FadeOut(marca),
                  FadeOut(fecho), FadeOut(regra), FadeOut(pergunta), run_time=0.6)

    # ------------------------------------------------------------------ ato 2
    def ato2_sequencial(self):
        self.trocar_titulo("2. O que o programa calcula")

        sub = Text("k(c) = nº de iterações até escapar, ou max_iter",
                   font_size=25, color=AZUL).next_to(self.titulo, DOWN, buff=0.16)
        self.play(FadeIn(sub), run_time=0.6)

        self.k = malha(340, 340, K=MAX_ITER)
        self.img = ImageMobject(colorir(self.k, MAX_ITER))
        self.img.set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        self.img.height = 4.1
        self.img.shift(DOWN * 0.55 + LEFT * 2.6)
        self.play(FadeIn(self.img), run_time=0.9)

        caixa = VGroup(
            Text("preto:  k = max_iter", font_size=23, color=WHITE),
            Text("dentro do conjunto — caro", font_size=21, color=CINZA),
            Text("claro:  k pequeno", font_size=23, color=AMAR),
            Text("escapa rápido — barato", font_size=21, color=CINZA),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.13).next_to(self.img, RIGHT, buff=0.75)
        self.play(FadeIn(caixa, shift=LEFT * 0.2), run_time=0.8)

        varre = Line(self.img.get_corner(UL), self.img.get_corner(UR),
                     color=VERM, stroke_width=4)
        self.play(FadeIn(varre), run_time=0.25)
        self.play(varre.animate.move_to(self.img.get_bottom() + UP * 0.02),
                  run_time=2.2, rate_func=linear)
        self.play(FadeOut(varre), run_time=0.25)

        nota = Text("Sequencial: uma linha após a outra — 5,5 s em 4000×4000 (medido)",
                    font_size=24, color=VERM).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(nota), run_time=0.6)
        self.wait(1.3)
        self.play(FadeOut(caixa), FadeOut(nota), FadeOut(sub), run_time=0.5)

    # ------------------------------------------------------------------ ato 3
    def ato3_paralelismo(self):
        self.trocar_titulo("3. Como paralelizamos")

        sub = Text("Cada pixel é independente — dividimos as linhas entre os processos",
                   font_size=24, color=CINZA).next_to(self.titulo, DOWN, buff=0.16)
        self.play(FadeIn(sub), self.img.animate.shift(LEFT * 0.7 + DOWN * 0.1), run_time=0.8)

        LIN, NP = self.k.shape[0], 4
        custo = self.k.sum(axis=1).astype(float)

        def painel(pesos):
            total, g = max(pesos), VGroup()
            for i, p in enumerate(pesos):
                barra = Rectangle(width=3.4 * p / total, height=0.4,
                                  fill_color=CORES_PROC[i], fill_opacity=0.92,
                                  stroke_width=0)
                rot = Text(f"proc {i}", font_size=19)
                linha = VGroup(rot, barra).arrange(RIGHT, buff=0.14)
                linha[1].align_to(linha, LEFT).shift(RIGHT * 0.95)
                g.add(linha)
            g.arrange(DOWN, aligned_edge=LEFT, buff=0.2)
            cab = Text("trabalho por processo", font_size=23,
                       weight=BOLD).next_to(g, UP, buff=0.28)
            return VGroup(cab, g).next_to(self.img, RIGHT, buff=0.8)

        # --- blocos contíguos ---
        alt = self.img.height / NP
        faixas = VGroup(*[
            Rectangle(width=self.img.width, height=alt, fill_color=CORES_PROC[i],
                      fill_opacity=0.45, stroke_color=WHITE, stroke_width=1.4)
            .move_to(self.img.get_top() + DOWN * alt * (i + 0.5))
            for i in range(NP)
        ])
        rot_b = Text("blocos contíguos", font_size=24, color=VERM)
        rot_b.next_to(self.img, UP, buff=0.14)
        peso_b = [custo[i * LIN // NP:(i + 1) * LIN // NP].sum() for i in range(NP)]
        pb = painel(peso_b)

        self.play(FadeIn(faixas), FadeIn(rot_b), run_time=0.7)
        self.play(FadeIn(pb, shift=LEFT * 0.2), run_time=0.8)
        diag = Text(f"desbalanceado: {max(peso_b)/min(peso_b):.0f}× entre o maior e o menor"
                    "   →   MPI np=4 dá 1,74×, pior que np=2",
                    font_size=23, color=VERM).to_edge(DOWN, buff=0.28)
        self.play(FadeIn(diag), run_time=0.6)
        self.wait(2.0)

        # --- linhas intercaladas ---
        n_list = 44
        listras = VGroup(*[
            Rectangle(width=self.img.width, height=self.img.height / n_list,
                      fill_color=CORES_PROC[i % NP], fill_opacity=0.45, stroke_width=0)
            .move_to(self.img.get_top() + DOWN * (self.img.height / n_list) * (i + 0.5))
            for i in range(n_list)
        ])
        rot_c = Text("linhas intercaladas (cíclica)", font_size=24, color=VERDE)
        rot_c.next_to(self.img, UP, buff=0.14)
        peso_c = [custo[i::NP].sum() for i in range(NP)]
        diag_c = Text(f"equilibrado: {max(peso_c)/min(peso_c):.2f}×"
                      "   →   MPI np=4 dá 3,58×",
                      font_size=23, color=VERDE).to_edge(DOWN, buff=0.28)

        self.play(FadeOut(faixas), FadeOut(rot_b), run_time=0.4)
        self.play(FadeIn(listras), FadeIn(rot_c), run_time=0.7)
        self.play(Transform(pb, painel(peso_c)), Transform(diag, diag_c), run_time=1.1)
        self.wait(2.2)

        # --- fecho ---
        self.play(FadeOut(listras), FadeOut(rot_c), FadeOut(pb), FadeOut(diag),
                  FadeOut(self.img), FadeOut(sub), run_time=0.7)
        final = VGroup(
            Text("O gargalo não é comunicação.", font_size=32, color=CINZA),
            Text("É desbalanceamento de carga.", font_size=36, weight=BOLD, color=VERDE),
        ).arrange(DOWN, buff=0.22)
        self.play(FadeIn(final, shift=UP * 0.2), run_time=0.9)
        self.wait(2.0)
