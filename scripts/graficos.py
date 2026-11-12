#!/usr/bin/env python3
"""Lê resultados/medicoes.csv e gera os gráficos exigidos no Marco 2.

Produz em resultados/:
  tempo_{omp,mpi}.png          tempo de execução por número de workers
  speedup_{omp,mpi}.png        speedup contra a curva ideal
  eficiencia_{omp,mpi}.png     eficiência (speedup / workers)
  escalonamento_omp.png        static x dynamic x guided
  decomposicao_mpi.png         bloco x cíclica
  comunicacao_mpi.png          fração do tempo gasta em comunicação
  escalabilidade_fraca.png     eficiência fraca: T_base / T_p
  amdahl_vs_medido.png         Amdahl x capacidade da máquina x medido
"""
import csv
import os
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DESTINO = os.path.join(RAIZ, "resultados")
ARQUIVO = os.path.join(DESTINO, "medicoes.csv")

# Variante preferida por versão nos gráficos gerais (a melhor de cada).
PADRAO = {"omp": "dynamic", "mpi": "ciclica"}
EIXO = {"omp": "número de threads", "mpi": "número de processos"}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def carregar():
    if not os.path.exists(ARQUIVO):
        sys.exit(f"não encontrei {ARQUIVO} — rode ./scripts/medir.sh antes")
    linhas = []
    with open(ARQUIVO) as f:
        for l in csv.DictReader(f):
            l["config"] = int(l["config"])
            l["tempo"] = float(l["tempo"])
            l["tam"] = f"{l['largura']}x{l['altura']}"
            l["lado"] = int(l["largura"])
            linhas.append(l)
    return linhas


def medias(linhas, chave):
    """chave(linha) -> tempo médio das repetições."""
    acc = defaultdict(list)
    for l in linhas:
        k = chave(l)
        if k is not None:
            acc[k].append(l["tempo"])
    return {k: sum(v) / len(v) for k, v in acc.items()}


def salvar(fig, nome):
    caminho = os.path.join(DESTINO, nome)
    fig.savefig(caminho, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("gerado:", os.path.relpath(caminho, RAIZ))


def curvas(forte, versao, tamanhos):
    """(tam) -> (xs, tempos, speedups, eficiencias) para a variante padrão."""
    variante = PADRAO[versao]
    base = medias([l for l in forte if l["versao"] == "seq"], lambda l: l["tam"])
    par = medias(
        [l for l in forte if l["versao"] == versao and l["variante"] == variante],
        lambda l: (l["tam"], l["config"]),
    )
    saida = {}
    for tam in tamanhos:
        if tam not in base:
            continue
        xs = sorted(c for (t, c) in par if t == tam)
        if not xs:
            continue
        ts = [par[(tam, x)] for x in xs]
        sp = [base[tam] / t for t in ts]
        ef = [s / x for s, x in zip(sp, xs)]
        saida[tam] = (xs, ts, sp, ef)
    return saida


def graficos_por_versao(forte, versao, tamanhos):
    dados = curvas(forte, versao, tamanhos)
    if not dados:
        return
    rotulo = f"{versao.upper()} ({PADRAO[versao]})"

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for tam, (xs, ts, _, _) in dados.items():
        ax.plot(xs, ts, marker="o", label=tam)
    ax.set(xlabel=EIXO[versao], ylabel="tempo (s)", title=f"Tempo — {rotulo}")
    ax.set_yscale("log")
    ax.grid(True, alpha=0.3, which="both")
    ax.legend(title="entrada")
    salvar(fig, f"tempo_{versao}.png")

    fig, ax = plt.subplots(figsize=(6, 4.5))
    todos = []
    for tam, (xs, _, sp, _) in dados.items():
        ax.plot(xs, sp, marker="o", label=tam)
        todos = xs
    ax.plot(todos, todos, "k--", alpha=0.35, label="ideal")
    ax.set(xlabel=EIXO[versao], ylabel="speedup", title=f"Speedup — {rotulo}")
    ax.set_xticks(todos)
    ax.grid(True, alpha=0.3)
    ax.legend(title="entrada")
    salvar(fig, f"speedup_{versao}.png")

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for tam, (xs, _, _, ef) in dados.items():
        ax.plot(xs, [100 * e for e in ef], marker="o", label=tam)
        todos = xs
    ax.axhline(100, color="k", ls="--", alpha=0.35, label="ideal")
    ax.set(xlabel=EIXO[versao], ylabel="eficiência (%)",
           title=f"Eficiência — {rotulo}", ylim=(0, 115))
    ax.set_xticks(todos)
    ax.grid(True, alpha=0.3)
    ax.legend(title="entrada")
    salvar(fig, f"eficiencia_{versao}.png")


def comparativo(forte, versao, variantes, tam, nome, titulo):
    base = medias([l for l in forte if l["versao"] == "seq"], lambda l: l["tam"])
    if tam not in base:
        return
    fig, ax = plt.subplots(figsize=(6, 4.5))
    todos = []
    for var in variantes:
        par = medias(
            [l for l in forte
             if l["versao"] == versao and l["variante"] == var and l["tam"] == tam],
            lambda l: l["config"],
        )
        if not par:
            continue
        xs = sorted(par)
        ax.plot(xs, [base[tam] / par[x] for x in xs], marker="o", label=var)
        todos = xs
    if not todos:
        plt.close(fig)
        return
    ax.plot(todos, todos, "k--", alpha=0.35, label="ideal")
    ax.set(xlabel=EIXO[versao], ylabel="speedup", title=f"{titulo} — entrada {tam}")
    ax.set_xticks(todos)
    ax.grid(True, alpha=0.3)
    ax.legend()
    salvar(fig, nome)


def comunicacao(forte, tam):
    acc = defaultdict(lambda: ([], []))
    for l in forte:
        if l["versao"] != "mpi" or l["tam"] != tam:
            continue
        c, m = num(l.get("calculo")), num(l.get("comunicacao"))
        if c is None or m is None:
            continue
        calc, com = acc[(l["variante"], l["config"])]
        calc.append(c)
        com.append(m)
    if not acc:
        return
    fig, ax = plt.subplots(figsize=(6, 4.5))
    for var in sorted({v for (v, _) in acc}):
        xs = sorted(c for (v, c) in acc if v == var)
        ys = []
        for x in xs:
            calc, com = acc[(var, x)]
            mc, mm = sum(calc) / len(calc), sum(com) / len(com)
            ys.append(100 * mm / (mc + mm))
        ax.plot(xs, ys, marker="o", label=var)
    ax.set(xlabel=EIXO["mpi"], ylabel="comunicação / tempo total (%)",
           title=f"Overhead de comunicação — MPI, entrada {tam}")
    ax.grid(True, alpha=0.3)
    ax.legend(title="decomposição")
    salvar(fig, "comunicacao_mpi.png")


def escalabilidade_fraca(fraca):
    if not fraca:
        return
    base = medias([l for l in fraca if l["versao"] == "seq"], lambda l: "base")
    if "base" not in base:
        return
    fig, ax = plt.subplots(figsize=(6, 4.5))
    todos = []
    for versao in ("omp", "mpi"):
        par = medias([l for l in fraca if l["versao"] == versao], lambda l: l["config"])
        if not par:
            continue
        xs = sorted(par)
        ax.plot(xs, [100 * base["base"] / par[x] for x in xs],
                marker="o", label=f"{versao.upper()} ({PADRAO[versao]})")
        todos = sorted(set(todos) | set(xs))
    ax.axhline(100, color="k", ls="--", alpha=0.35, label="ideal")
    ax.set(xlabel="workers (entrada cresce com √p)", ylabel="eficiência fraca (%)",
           title="Escalabilidade fraca", ylim=(0, 115))
    ax.set_xticks(todos)
    ax.grid(True, alpha=0.3)
    ax.legend()
    salvar(fig, "escalabilidade_fraca.png")


def capacidade(copias):
    """N -> soma das velocidades de N cópias simultâneas, relativas a uma sozinha.

    É o speedup que um escalonamento perfeito alcançaria nesta máquina: cada
    núcleo entra com a velocidade que realmente tem quando todos estão ocupados.
    """
    sozinha = [l["tempo"] for l in copias if l["config"] == 1]
    if not sozinha:
        return {}
    t1 = sum(sozinha) / len(sozinha)
    por_rodada = defaultdict(float)
    for l in copias:
        por_rodada[(l["config"], l["repeticao"])] += t1 / l["tempo"]
    acc = defaultdict(list)
    for (n, _), s in por_rodada.items():
        acc[n].append(s)
    return {n: sum(v) / len(v) for n, v in acc.items()}


def amdahl_vs_medido(forte, copias, tam):
    """Compara o teto de Amdahl e a capacidade da máquina com o speedup medido."""
    # f vem do perfilamento do baseline: ./bin/mandelbrot_seq 4000 4000 1000 --perfil
    F = 0.9989
    base = medias([l for l in forte if l["versao"] == "seq"], lambda l: l["tam"])
    if tam not in base:
        return
    par = medias(
        [l for l in forte if l["versao"] == "omp" and l["variante"] == "dynamic"
         and l["tam"] == tam],
        lambda l: l["config"],
    )
    if not par:
        return
    xs = sorted(par)
    medido = [base[tam] / par[x] for x in xs]
    teto = [1 / ((1 - F) + F / x) for x in xs]
    cap = capacidade([l for l in copias if l["tam"] == tam])

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.plot(xs, teto, marker="s", ls="--", label=f"Amdahl (f = {F})")
    if cap:
        ns = sorted(cap)
        ax.plot(ns, [cap[n] for n in ns], marker="^", ls=":",
                label="capacidade da máquina (N cópias do seq)")
    ax.plot(xs, medido, marker="o", label="medido (OpenMP dynamic)")
    for x, t, m in zip(xs, teto, medido):
        if t - m > 0.3:
            ax.annotate("", xy=(x, m), xytext=(x, t),
                        arrowprops=dict(arrowstyle="<->", color="#c33", lw=1))
            ax.text(x + 0.12, (t + m) / 2, f"{t - m:.2f}x", color="#c33",
                    fontsize=9, va="center")
    ax.set(xlabel="número de workers", ylabel="speedup",
           title=f"Teto de Amdahl x speedup medido — entrada {tam}")
    ax.set_xticks(xs)
    ax.grid(True, alpha=0.3)
    ax.legend()
    salvar(fig, "amdahl_vs_medido.png")


def main():
    linhas = carregar()
    forte = [l for l in linhas if l["experimento"] == "forte"]
    fraca = [l for l in linhas if l["experimento"] == "fraca"]
    copias = [l for l in linhas if l["experimento"] == "teto"]
    tamanhos = sorted({l["tam"] for l in forte}, key=lambda t: int(t.split("x")[0]))
    maior = tamanhos[-1] if tamanhos else None

    for versao in ("omp", "mpi"):
        graficos_por_versao(forte, versao, tamanhos)

    if maior:
        comparativo(forte, "omp", ["static", "dynamic", "guided"], maior,
                    "escalonamento_omp.png", "Políticas de escalonamento (OpenMP)")
        comparativo(forte, "mpi", ["bloco", "ciclica"], maior,
                    "decomposicao_mpi.png", "Decomposição de domínio (MPI)")
        comunicacao(forte, maior)
        amdahl_vs_medido(forte, copias, maior)
    escalabilidade_fraca(fraca)


if __name__ == "__main__":
    main()
