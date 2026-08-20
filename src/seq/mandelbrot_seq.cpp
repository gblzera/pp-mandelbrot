// ============================================================================
// PROVISÓRIO — substituto temporário até o professor entregar o código
// sequencial de referência do problema 3 (Conjunto de Mandelbrot).
// Serve apenas para montar e testar o pipeline (Makefile, medição, gráficos).
// O código oficial substitui este arquivo e define o gabarito; a partir daí
// não se altera a lógica de cálculo nem a entrada dele.
//
// Uso: mandelbrot_seq [largura] [altura] [max_iter] [--dump ARQ] [--perfil]
//   --dump ARQ  grava a matriz de iterações (int32 bruto) para validação
//               elemento a elemento contra as versões paralelas.
//   --perfil    imprime o tempo por trecho (alocação / cálculo / checksum).
// Ambas as opções ficam FORA do trecho cronometrado como "calculo".
// ============================================================================
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <chrono>

using Relogio = std::chrono::steady_clock;
static double desde(Relogio::time_point t) {
    return std::chrono::duration<double>(Relogio::now() - t).count();
}

int main(int argc, char** argv) {
    int largura = 2000, altura = 2000, max_iter = 1000;
    const char* dump = nullptr;
    bool perfil = false;

    int pos = 0;
    for (int a = 1; a < argc; a++) {
        if (std::strcmp(argv[a], "--dump") == 0 && a + 1 < argc) dump = argv[++a];
        else if (std::strcmp(argv[a], "--perfil") == 0)          perfil = true;
        else if (pos == 0) { largura  = std::atoi(argv[a]); pos++; }
        else if (pos == 1) { altura   = std::atoi(argv[a]); pos++; }
        else if (pos == 2) { max_iter = std::atoi(argv[a]); pos++; }
    }

    const double x_min = -2.0, x_max = 1.0;
    const double y_min = -1.5, y_max = 1.5;

    auto t_aloc = Relogio::now();
    std::vector<int> iteracoes((size_t)largura * altura);
    double tempo_aloc = desde(t_aloc);

    auto inicio = Relogio::now();

    for (int j = 0; j < altura; j++) {
        double ci = y_min + (y_max - y_min) * j / (altura - 1);
        for (int i = 0; i < largura; i++) {
            double cr = x_min + (x_max - x_min) * i / (largura - 1);
            double zr = 0.0, zi = 0.0;
            int iter = 0;
            while (zr * zr + zi * zi <= 4.0 && iter < max_iter) {
                double tmp = zr * zr - zi * zi + cr;
                zi = 2.0 * zr * zi + ci;
                zr = tmp;
                iter++;
            }
            iteracoes[(size_t)j * largura + i] = iter;
        }
    }

    double tempo = desde(inicio);

    auto t_chk = Relogio::now();
    uint64_t checksum = 0;
    for (int v : iteracoes) checksum += (uint64_t)v;
    double tempo_chk = desde(t_chk);

    if (dump) {
        FILE* f = std::fopen(dump, "wb");
        if (!f) { std::perror("dump"); return 1; }
        std::fwrite(iteracoes.data(), sizeof(int), iteracoes.size(), f);
        std::fclose(f);
    }

    // Uma linha key=valor, fácil de parsear pelo scripts/medir.sh.
    std::printf("versao=seq config=1 largura=%d altura=%d max_iter=%d checksum=%llu tempo=%.6f\n",
                largura, altura, max_iter, (unsigned long long)checksum, tempo);

    if (perfil) {
        double total = tempo_aloc + tempo + tempo_chk;
        std::printf("# perfil por trecho (total=%.6f s)\n", total);
        std::printf("#   alocacao : %9.6f s  (%5.2f%%)\n", tempo_aloc, 100 * tempo_aloc / total);
        std::printf("#   calculo  : %9.6f s  (%5.2f%%)  <- hotspot\n", tempo, 100 * tempo / total);
        std::printf("#   checksum : %9.6f s  (%5.2f%%)\n", tempo_chk, 100 * tempo_chk / total);
        std::printf("# fracao paralelizavel estimada (calculo/total) = %.4f\n", tempo / total);
        std::printf("# Amdahl, speedup maximo com P->inf = %.2fx\n", total / (total - tempo));
    }
    return 0;
}
