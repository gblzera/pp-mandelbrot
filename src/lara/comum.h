#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include <string>
#include <vector>

// Mesma matematica e os mesmos parametros em TODAS as versoes.
struct Config {
    int largura = 400; // colunas (pixels por linha)
    int altura = 600;  // linhas
    int max_iter = 1000;
};
inline Config ler_config(int argc, char** argv) {
    Config c;
    if (argc > 1) c.largura = std::atoi(argv[1]);
    if (argc > 2) c.altura = std::atoi(argv[2]);
    if (argc > 3) c.max_iter = std::atoi(argv[3]);
    if (c.largura < 2 || c.altura < 2 || c.max_iter < 1)
        throw std::runtime_error("Uso: programa [largura>=2] [altura>=2] [max_iter>=1]");
    return c;
}
// Um pixel e independente de todos os outros; as iteracoes DENTRO dele dependem
// do valor anterior de z. Por isso paralelizamos pixels, nao o while.
inline int calcular_pixel(int x, int y, const Config& c) {
    const double cr = -2.0 + 3.0 * x / (c.largura - 1);
    const double ci = -1.5 + 3.0 * y / (c.altura - 1);
    double zr = 0.0, zi = 0.0; // variaveis LOCAIS: nao compartilhadas
    int iter = 0;
    while (zr*zr + zi*zi <= 4.0 && iter < c.max_iter) {
        const double proximo_zr = zr*zr - zi*zi + cr;
        zi = 2.0*zr*zi + ci;
        zr = proximo_zr;
        ++iter;
    }
    return iter;
}
inline uint64_t checksum_imagem(const std::vector<int>& imagem) {
    uint64_t soma = 0;
    for (int v : imagem) soma += static_cast<uint64_t>(v);
    return soma;
}
inline double relogio() {
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
}
inline void imprimir(const char* versao, const char* modelo, const Config& c,
                    int recursos, uint64_t checksum, double segundos,
                    double calculo = -1.0, double comunicacao = -1.0,
                    double desbalanceamento = -1.0) {
    std::printf("versao=%s modelo=%s recursos=%d largura=%d altura=%d max_iter=%d "
                "checksum=%llu tempo=%.6f calculo=%.6f comunicacao=%.6f desbalanceamento=%.3f\n",
                versao, modelo, recursos, c.largura, c.altura, c.max_iter,
                (unsigned long long)checksum, segundos, calculo, comunicacao, desbalanceamento);
}
