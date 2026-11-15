
#include "comum.h"
#include <omp.h>
#include <iostream>
#include <cstdlib>

int main(int argc, char** argv) {
    try {
        const Config c = ler_config(argc, argv);

        // Quantidade de threads trabalhadoras
        const int threads =
            argc > 4 ? std::atoi(argv[4]) : 4;

        // Tamanho do bloco de iteracoes
        const int chunk =
            argc > 5 ? std::atoi(argv[5]) : 16;

        if (threads < 1 || chunk < 1) {
            throw std::runtime_error(
                "Uso: ./openmp largura altura max_iter threads chunk"
            );
        }

        // Vetor que armazena os pixels calculados
        std::vector<int> imagem(
            (size_t)c.largura * c.altura
        );

        // Escalonamento dinamico
        omp_set_schedule(omp_sched_dynamic, chunk);

        // Inicio da medicao
        const double inicio = relogio();

        // Todas as threads participam do calculo
        #pragma omp parallel for collapse(2) \
            schedule(runtime) num_threads(threads)

        for (int y = 0; y < c.altura; ++y) {
            for (int x = 0; x < c.largura; ++x) {

                imagem[(size_t)y * c.largura + x] =
                    calcular_pixel(x, y, c);

            }
        }

        // Fim da medicao
        const double tempo = relogio() - inicio;

        imprimir(
            "openmp",
            "todos",
            c,
            threads,
            checksum_imagem(imagem),
            tempo,
            tempo,
            0
        );

    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n';
        return 1;
    }

    return 0;
}
