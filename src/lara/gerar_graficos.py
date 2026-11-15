
import csv
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Arquivos com os resultados dos experimentos
ARQUIVO_OPENMP = "resultados_amdahl.csv"
ARQUIVO_MPI = "resultados_escalabilidade_mpi_hibrido.csv"

# Pasta onde os graficos serao salvos
PASTA = Path("graficos_mandelbrot")
PASTA.mkdir(exist_ok=True)

CHECKSUM = "41237493"

NOMES = {
    "openmp_todos": "OpenMP todos",
    "mpi_todos": "MPI todos",
    "mpi_mestre": "MPI mestre",
    "hibrido_todos": "Hibrido todos",
    "hibrido_mestre": "Hibrido mestre",
}

dados = defaultdict(list)
configuracoes = {}

# 1. Ler resultados OpenMP
with open(ARQUIVO_OPENMP, newline="") as arquivo:
    for linha in csv.DictReader(arquivo):
        if linha["checksum"] != CHECKSUM:
            raise ValueError("Checksum invalido no OpenMP")

        recursos = int(linha["threads"])
        chave = ("openmp_todos", recursos)

        dados[chave].append(float(linha["tempo"]))

        configuracoes[chave] = {
            "ranks": 0,
            "threads_por_rank": recursos,
            "recursos_calculo": recursos,
        }

# 2. Ler resultados MPI e Hibrido
with open(ARQUIVO_MPI, newline="") as arquivo:
    for linha in csv.DictReader(arquivo):
        if linha["checksum"] != CHECKSUM:
            raise ValueError("Checksum invalido no MPI/Hibrido")

        modelo = linha["versao"] + "_" + linha["modelo"]
        recursos = int(linha["recursos_calculo"])
        chave = (modelo, recursos)

        dados[chave].append(float(linha["tempo"]))

        configuracoes[chave] = {
            "ranks": int(linha["ranks"]),
            "threads_por_rank": int(linha["threads_por_rank"]),
            "recursos_calculo": recursos,
        }

# 3. Calcular estatisticas
resumo = defaultdict(list)

for (modelo, recursos), tempos in dados.items():
    if len(tempos) != 30:
        raise ValueError(
            f"{modelo}, {recursos} recursos: "
            f"esperadas 30 execucoes, encontradas {len(tempos)}"
        )

    resumo[modelo].append({
        "recursos": recursos,
        "mediana": statistics.median(tempos),
        "media": statistics.mean(tempos),
        "minimo": min(tempos),
        "maximo": max(tempos),
        **configuracoes[(modelo, recursos)]
    })

# 4. Calcular speedup e eficiencia
for modelo, linhas in resumo.items():
    linhas.sort(key=lambda x: x["recursos"])

    referencia = linhas[0]
    tempo_base = referencia["mediana"]
    recursos_base = referencia["recursos"]

    for linha in linhas:
        recursos = linha["recursos"]

        linha["speedup"] = tempo_base / linha["mediana"]

        # Eficiencia relativa a configuracao inicial
        fator_recursos = recursos / recursos_base

        linha["eficiencia"] = (
            linha["speedup"] / fator_recursos * 100
        )

# 5. Salvar tabela resumida
saida_csv = PASTA / "resumo_escalabilidade.csv"

with open(saida_csv, "w", newline="") as arquivo:
    colunas = [
        "modelo", "recursos", "ranks", "threads_por_rank",
        "mediana", "media", "minimo", "maximo",
        "speedup", "eficiencia"
    ]

    escritor = csv.DictWriter(arquivo, fieldnames=colunas)
    escritor.writeheader()

    for modelo, linhas in resumo.items():
        for linha in linhas:
            escritor.writerow({
                "modelo": modelo,
                **{
                    coluna: linha[coluna]
                    for coluna in colunas[1:]
                }
            })

# 6. Funcao para gerar graficos
def criar_grafico(campo, titulo, eixo_y, nome_arquivo):
    plt.figure(figsize=(11, 6))

    for modelo, linhas in resumo.items():
        x = [linha["recursos"] for linha in linhas]
        y = [linha[campo] for linha in linhas]

        plt.plot(
            x, y,
            marker="o",
            linewidth=2,
            label=NOMES[modelo]
        )

    plt.title(titulo)
    plt.xlabel("Recursos calculadores (ranks ou threads)")
    plt.ylabel(eixo_y)
    plt.xticks([1, 2, 4, 6, 8, 12, 16])
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    plt.savefig(PASTA / nome_arquivo, dpi=300)
    plt.close()

# 7. Gerar os tres graficos
criar_grafico(
    "mediana",
    "Mandelbrot - Tempo de execucao",
    "Tempo mediano (segundos)",
    "01_tempo.png"
)

criar_grafico(
    "speedup",
    "Mandelbrot - Speedup relativo",
    "Speedup (vezes)",
    "02_speedup.png"
)

criar_grafico(
    "eficiencia",
    "Mandelbrot - Eficiencia relativa",
    "Eficiencia (%)",
    "03_eficiencia.png"
)

# 8. Mostrar resultados
print("\nRESULTADOS DE ESCALABILIDADE\n")

for modelo, linhas in resumo.items():
    print(f"\n{NOMES[modelo]}")
    print("Recursos | Mediana (s) | Speedup | Eficiencia (%)")

    for linha in linhas:
        print(
            f"{linha['recursos']:>8} | "
            f"{linha['mediana']:>11.6f} | "
            f"{linha['speedup']:>7.3f} | "
            f"{linha['eficiencia']:>14.2f}"
        )

print("\nArquivos gerados em:", PASTA.resolve())
print("01_tempo.png")
print("02_speedup.png")
print("03_eficiencia.png")
print("resumo_escalabilidade.csv")
