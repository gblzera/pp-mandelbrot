"""Animação didática do modelo matemático por trás do projeto.

Três cenas, na ordem em que o professor pediu:
  Orbita       — a matemática do modelo e o problema que ele resolve
  TempoEscape  — o que o programa calcula, sequencialmente
  Paralelizar  — por que blocos contíguos falham e a cíclica funciona

Sem LaTeX: usa Text com unicode, então roda em máquina sem distribuição TeX.
Render:  manim -qh animacao/mandelbrot.py Orbita TempoEscape Paralelizar
"""
import numpy as np
from manim import *

AZUL, VERDE, VERM, CINZA = "#3B7DD8", "#2FA84F", "#D1495B", "#888888"
R_ESCAPE = 2.0


def escape(c, K=200):
    """Tempo de escape k(c): itera z <- z^2 + c e devolve (k, orbita)."""
    z, orb = 0j, [0j]
    for n in range(1, K + 1):
        z = z * z + c
        orb.append(z)
        if abs(z) > R_ESCAPE:
            return n, orb
    return K, orb


def malha(w, h, K=120, xr=(-2.0, 1.0), yr=(-1.5, 1.5)):
    """Matriz de tempos de escape, vetorizada — é o que o baseline calcula."""
    x = np.linspace(*xr, w)
    y = np.linspace(*yr, h)
    c = x[None, :] + 1j * y[:, None]
    z = np.zeros_like(c)
    k = np.zeros(c.shape, dtype=int)
    vivo = np.ones(c.shape, dtype=bool)
    for n in range(K):
        z[vivo] = z[vivo] ** 2 + c[vivo]
        escapou = vivo & (np.abs(z) > R_ESCAPE)
        k[escapou] = n + 1
        vivo &= ~escapou
    k[vivo] = K
    return k


PALETA = np.array([[255, 247, 214], [245, 158, 66], [150, 40, 90], [30, 45, 120]]) / 255.0


def colorir(k, K=120):
    """k -> RGB. Preto = pertence ao conjunto (caro). Claro = escapa rápido.

    Escala logarítmica porque a maioria dos pontos escapa em poucas iterações:
    em escala linear a imagem satura em branco e não se enxerga estrutura.
    """
    dentro = k >= K
    t = np.log1p(k) / np.log1p(K)
    idx = np.clip(t, 0, 1) * (len(PALETA) - 1)
    i0 = np.clip(np.floor(idx), 0, len(PALETA) - 2).astype(int)
    f = (idx - i0)[..., None]
    rgb = PALETA[i0] * (1 - f) + PALETA[i0 + 1] * f
    rgb[dentro] = 0.02
    return (rgb * 255).astype(np.uint8)


class Orbita(Scene):
    """O modelo: M = { c : a órbita de 0 sob z <- z^2 + c permanece limitada }."""

    def construct(self):
        titulo = Text("O modelo: a órbita do zero", weight=BOLD, font_size=40)
        regra = Text("z(n+1) = z(n)² + c,   começando em z(0) = 0", font_size=30, color=AZUL)
        VGroup(titulo, regra).arrange(DOWN, buff=0.3).to_edge(UP, buff=0.5)
        self.play(Write(titulo), run_time=0.8)
        self.play(FadeIn(regra, shift=UP * 0.2), run_time=0.8)

        plano = ComplexPlane(
            x_range=[-2.5, 2.5, 1], y_range=[-2, 2, 1],
            background_line_style={"stroke_opacity": 0.25},
        ).scale(1.05).shift(DOWN * 0.6)
        disco = Circle(radius=plano.n2p(2)[0] - plano.n2p(0)[0],
                       color=VERM, stroke_width=3).move_to(plano.n2p(0))
        rotulo = Text("|z| = 2  →  escapou", font_size=22, color=VERM)
        rotulo.next_to(disco, UP, buff=0.08).shift(RIGHT * 2.2)
        self.play(Create(plano), run_time=1.0)
        self.play(Create(disco), FadeIn(rotulo), run_time=0.8)

        legenda = Text("", font_size=26).to_edge(DOWN, buff=0.45)
        self.add(legenda)

        for c, cor, texto in [
            (-0.5 + 0.55j, VERDE, "c = −0,5 + 0,55i  →  órbita limitada  →  c ∈ M"),
            (0.36 + 0.36j, VERM, "c = 0,36 + 0,36i  →  escapa  →  c ∉ M"),
        ]:
            k, orb = escape(c, K=28)
            pc = Dot(plano.n2p(c), color=cor, radius=0.075)
            marca = Text("c", font_size=24, color=cor).next_to(pc, UR, buff=0.05)
            novo = Text(texto, font_size=26, color=cor).to_edge(DOWN, buff=0.45)
            self.play(FadeIn(pc), FadeIn(marca), Transform(legenda, novo), run_time=0.7)

            pontos, tracos = VGroup(), VGroup()
            for i in range(1, min(len(orb), 16)):
                a, b = orb[i - 1], orb[i]
                if abs(b) > 3.2:
                    break
                seg = Line(plano.n2p(a), plano.n2p(b), color=cor,
                           stroke_width=2.5, stroke_opacity=0.65)
                pt = Dot(plano.n2p(b), color=cor, radius=0.045)
                tracos.add(seg); pontos.add(pt)
                self.play(Create(seg), FadeIn(pt), run_time=0.13)
            self.wait(0.5)
            self.play(FadeOut(pontos), FadeOut(tracos), FadeOut(pc), FadeOut(marca),
                      run_time=0.4)

        fecho = VGroup(
            Text("Escape é demonstrável em tempo finito.", font_size=27, color=VERM),
            Text("Permanência, não — por isso existe o max_iter.", font_size=27, color=VERDE),
        ).arrange(DOWN, buff=0.18).to_edge(DOWN, buff=0.35)
        self.play(FadeOut(legenda), FadeIn(fecho), run_time=0.8)
        self.wait(1.4)


class TempoEscape(Scene):
    """O que o programa calcula: k(c) pixel a pixel, sequencialmente."""

    def construct(self):
        titulo = Text("O que o programa calcula", weight=BOLD, font_size=40).to_edge(UP, buff=0.45)
        sub = Text("k(c) = nº de iterações até escapar (ou max_iter)",
                   font_size=27, color=AZUL).next_to(titulo, DOWN, buff=0.18)
        self.play(Write(titulo), FadeIn(sub), run_time=1.0)

        k = malha(360, 360)
        img = ImageMobject(colorir(k)).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        img.height = 4.3
        img.shift(DOWN * 0.55 + LEFT * 2.4)
        self.play(FadeIn(img), run_time=1.0)

        caixa = VGroup(
            Text("preto:  k = max_iter", font_size=25, color=WHITE),
            Text("→ pertence ao conjunto, caro", font_size=23, color=CINZA),
            Text("claro:  k pequeno", font_size=25, color=AZUL),
            Text("→ escapa rápido, barato", font_size=23, color=CINZA),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.16)
        caixa.next_to(img, RIGHT, buff=0.7)
        self.play(FadeIn(caixa, shift=LEFT * 0.2), run_time=0.9)

        varre = Line(img.get_corner(UL), img.get_corner(UR), color=VERM, stroke_width=4)
        self.play(FadeIn(varre), run_time=0.3)
        self.play(varre.animate.move_to(img.get_bottom() + UP * 0.02),
                  run_time=2.4, rate_func=linear)
        self.play(FadeOut(varre), run_time=0.3)

        nota = Text("Sequencial: uma linha após a outra.", font_size=27, color=VERM)
        nota.to_edge(DOWN, buff=0.35)
        self.play(FadeIn(nota), run_time=0.7)
        self.wait(1.3)


class Paralelizar(Scene):
    """Como paralelizamos: blocos contíguos falham, cíclica equilibra."""

    def construct(self):
        titulo = Text("Como paralelizar", weight=BOLD, font_size=40).to_edge(UP, buff=0.4)
        self.play(Write(titulo), run_time=0.7)

        # K = 1000 é o mesmo max_iter da campanha de medição, para que o
        # desbalanceamento mostrado aqui seja comparável ao do relatório.
        LIN, NP, K = 200, 4, 1000
        k = malha(200, LIN, K=K)
        custo = k.sum(axis=1).astype(float)
        cores = [AZUL, VERDE, "#E8A33D", VERM]

        img = ImageMobject(colorir(k, K)).set_resampling_algorithm(RESAMPLING_ALGORITHMS["nearest"])
        img.height = 3.9
        img.shift(LEFT * 3.3 + DOWN * 0.35)
        self.add(img)

        def barras(pesos, titulo_txt):
            total = max(pesos)
            g = VGroup()
            for i, p in enumerate(pesos):
                b = Rectangle(width=3.6 * p / total, height=0.42,
                              fill_color=cores[i], fill_opacity=0.9, stroke_width=0)
                rot = Text(f"proc {i}", font_size=20).next_to(b, LEFT, buff=0.15)
                g.add(VGroup(rot, b).arrange(RIGHT, buff=0.15))
            g.arrange(DOWN, aligned_edge=LEFT, buff=0.22)
            cab = Text(titulo_txt, font_size=25, weight=BOLD).next_to(g, UP, buff=0.3)
            return VGroup(cab, g)

        # --- decomposição em blocos contíguos ---
        alt = img.height / NP
        faixas = VGroup(*[
            Rectangle(width=img.width, height=alt, fill_color=cores[i],
                      fill_opacity=0.42, stroke_color=WHITE, stroke_width=1.5)
            .move_to(img.get_top() + DOWN * alt * (i + 0.5))
            for i in range(NP)
        ])
        rot_b = Text("blocos contíguos", font_size=26, color=VERM).next_to(img, UP, buff=0.18)
        peso_b = [custo[i * LIN // NP:(i + 1) * LIN // NP].sum() for i in range(NP)]
        painel_b = barras(peso_b, "trabalho por processo").shift(RIGHT * 2.9 + DOWN * 0.3)

        self.play(FadeIn(faixas), FadeIn(rot_b), run_time=0.8)
        self.play(FadeIn(painel_b, shift=LEFT * 0.2), run_time=0.9)
        diag = Text(f"desbalanceado: {max(peso_b)/min(peso_b):.0f}× entre o maior e o menor",
                    font_size=25, color=VERM).to_edge(DOWN, buff=0.3)
        self.play(FadeIn(diag), run_time=0.7)
        self.wait(1.6)

        # --- decomposição cíclica ---
        listras = VGroup(*[
            Rectangle(width=img.width, height=img.height / 40, fill_color=cores[i % NP],
                      fill_opacity=0.42, stroke_width=0)
            .move_to(img.get_top() + DOWN * (img.height / 40) * (i + 0.5))
            for i in range(40)
        ])
        rot_c = Text("linhas intercaladas (cíclica)", font_size=26, color=VERDE)
        rot_c.next_to(img, UP, buff=0.18)
        peso_c = [custo[i::NP].sum() for i in range(NP)]
        painel_c = barras(peso_c, "trabalho por processo").shift(RIGHT * 2.9 + DOWN * 0.3)
        diag_c = Text(f"equilibrado: {max(peso_c)/min(peso_c):.2f}× entre o maior e o menor",
                      font_size=25, color=VERDE).to_edge(DOWN, buff=0.3)

        self.play(FadeOut(faixas), FadeOut(rot_b), run_time=0.4)
        self.play(FadeIn(listras), FadeIn(rot_c), run_time=0.8)
        self.play(Transform(painel_b, painel_c), Transform(diag, diag_c), run_time=1.1)
        self.wait(2.0)
