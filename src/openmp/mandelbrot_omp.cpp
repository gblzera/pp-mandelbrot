// ============================================================================
// Versão OpenMP (memória compartilhada).
// Parte do sequencial provisório de src/seq/; o oficial ainda não foi recebido.
//
// Decisões documentadas no relatório:
//  - paralelização do laço externo (linhas): cada linha é independente;
//  - schedule(runtime): a política vem de OMP_SCHEDULE, o que permite comparar
//    static/dynamic/guided sem recompilar. O custo por pixel varia em ordens de
//    grandeza (pontos dentro do conjunto gastam max_iter iterações), então o
//    desbalanceamento de carga é o ponto central do estudo;
//  - reduction(+:checksum) trata a condição de corrida na acumulação. Escolhido
//    sobre critical (serializa a região inteira) e atomic (uma operação atômica
//    por pixel, tráfego de coerência a cada iteração): reduction dá a cada
//    thread uma cópia privada e combina uma única vez no fim, evitando também
//    false sharing na variável acumuladora.
//
// Uso: mandelbrot_omp [largura] [altura] [max_iter] [--dump ARQ]
// ============================================================================
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <omp.h>

int main(int argc, char** argv) {
    int largura = 2000, altura = 2000, max_iter = 1000;
    const char* dump = nullptr;

    int pos = 0;
    for (int a = 1; a < argc; a++) {
        if (std::strcmp(argv[a], "--dump") == 0 && a + 1 < argc) dump = argv[++a];
        else if (pos == 0) { largura  = std::atoi(argv[a]); pos++; }
        else if (pos == 1) { altura   = std::atoi(argv[a]); pos++; }
        else if (pos == 2) { max_iter = std::atoi(argv[a]); pos++; }
    }

    const double x_min = -2.0, x_max = 1.0;
    const double y_min = -1.5, y_max = 1.5;

    std::vector<int> iteracoes((size_t)largura * altura);
    uint64_t checksum = 0;

    double inicio = omp_get_wtime();

    #pragma omp parallel for schedule(runtime) reduction(+:checksum)
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
            checksum += (uint64_t)iter;
        }
    }

    double tempo = omp_get_wtime() - inicio;

    if (dump) {
        FILE* f = std::fopen(dump, "wb");
        if (!f) { std::perror("dump"); return 1; }
        std::fwrite(iteracoes.data(), sizeof(int), iteracoes.size(), f);
        std::fclose(f);
    }

    const char* sched = std::getenv("OMP_SCHEDULE");
    std::printf("versao=omp config=%d escalonamento=%s largura=%d altura=%d max_iter=%d checksum=%llu tempo=%.6f\n",
                omp_get_max_threads(), sched ? sched : "padrao",
                largura, altura, max_iter, (unsigned long long)checksum, tempo);
    return 0;
}
