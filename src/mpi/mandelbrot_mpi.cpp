// ============================================================================
// Versão MPI (memória distribuída).
// Parte do sequencial provisório de src/seq/; o oficial ainda não foi recebido.
//
// Decisões documentadas no relatório:
//  - decomposição de domínio por blocos contíguos de linhas. É a decomposição
//    estática ingênua e, para o Mandelbrot, o pior caso: as linhas caras estão
//    concentradas no meio da imagem, então o rank do meio vira o gargalo.
//    MANTIDA DE PROPÓSITO como termo de comparação — a variante intercalada
//    (DECOMP=ciclica) distribui as linhas com passo nprocs e equilibra a carga.
//    Selecionável em tempo de execução pela variável de ambiente DECOMP, para
//    que as duas curvas saiam da mesma campanha de medição.
//  - operações coletivas: MPI_Gatherv reúne a imagem completa no rank 0 (é a
//    comunicação real do programa, ~64 MB em 4000x4000) e MPI_Reduce combina o
//    checksum e os tempos.
//  - o tempo reportado é o MÁXIMO entre os processos: o mais lento define o
//    total. Cálculo e comunicação são cronometrados separadamente, para que o
//    overhead de comunicação em função de nprocs seja medível diretamente.
//
// Uso: mpirun -np P mandelbrot_mpi [largura] [altura] [max_iter] [--dump ARQ]
//      DECOMP=bloco (padrão) | ciclica
// ============================================================================
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>
#include <algorithm>
#include <mpi.h>

int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, nprocs;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &nprocs);

    int largura = 2000, altura = 2000, max_iter = 1000;
    const char* dump = nullptr;

    int pos = 0;
    for (int a = 1; a < argc; a++) {
        if (std::strcmp(argv[a], "--dump") == 0 && a + 1 < argc) dump = argv[++a];
        else if (pos == 0) { largura  = std::atoi(argv[a]); pos++; }
        else if (pos == 1) { altura   = std::atoi(argv[a]); pos++; }
        else if (pos == 2) { max_iter = std::atoi(argv[a]); pos++; }
    }

    const char* env_decomp = std::getenv("DECOMP");
    const bool ciclica = env_decomp && std::strcmp(env_decomp, "ciclica") == 0;
    const char* nome_decomp = ciclica ? "ciclica" : "bloco";

    const double x_min = -2.0, x_max = 1.0;
    const double y_min = -1.5, y_max = 1.5;

    // Quantas linhas cabem a este rank. As duas decomposições dão a MESMA
    // contagem por rank; o que muda é QUAIS linhas.
    //   bloco   : faixa contígua [linha_inicial, linha_inicial + minhas_linhas)
    //   ciclica : linhas rank, rank+nprocs, rank+2*nprocs, ...
    const int base  = altura / nprocs;
    const int resto = altura % nprocs;
    const int minhas_linhas = base + (rank < resto ? 1 : 0);
    const int linha_inicial = rank * base + std::min(rank, resto);

    auto linha_global = [&](int j_local) {
        return ciclica ? rank + j_local * nprocs : linha_inicial + j_local;
    };

    std::vector<int> faixa((size_t)largura * minhas_linhas);

    MPI_Barrier(MPI_COMM_WORLD);
    const double t0 = MPI_Wtime();

    uint64_t checksum_local = 0;
    for (int j = 0; j < minhas_linhas; j++) {
        const int j_global = linha_global(j);
        double ci = y_min + (y_max - y_min) * j_global / (altura - 1);
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
            faixa[(size_t)j * largura + i] = iter;
            checksum_local += (uint64_t)iter;
        }
    }

    const double t1 = MPI_Wtime();          // fim do cálculo local

    // ---- comunicação: reconstrói a imagem inteira no rank 0 ----------------
    std::vector<int> contagens(nprocs), deslocamentos(nprocs);
    for (int r = 0; r < nprocs; r++) {
        const int linhas_r = base + (r < resto ? 1 : 0);
        contagens[r]     = largura * linhas_r;
        deslocamentos[r] = largura * (r * base + std::min(r, resto));
    }

    std::vector<int> imagem;
    if (rank == 0) imagem.resize((size_t)largura * altura);

    MPI_Gatherv(faixa.data(), largura * minhas_linhas, MPI_INT,
                rank == 0 ? imagem.data() : nullptr,
                contagens.data(), deslocamentos.data(), MPI_INT,
                0, MPI_COMM_WORLD);

    uint64_t checksum = 0;
    MPI_Reduce(&checksum_local, &checksum, 1, MPI_UINT64_T, MPI_SUM, 0, MPI_COMM_WORLD);

    const double t2 = MPI_Wtime();          // fim da comunicação

    double calc_local = t1 - t0, comm_local = t2 - t1, total_local = t2 - t0;
    double calc = 0.0, comm = 0.0, tempo = 0.0;
    MPI_Reduce(&calc_local,  &calc,  1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&comm_local,  &comm,  1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    MPI_Reduce(&total_local, &tempo, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    // Desbalanceamento: razão entre o rank mais lento e o mais rápido.
    double calc_min = 0.0;
    MPI_Reduce(&calc_local, &calc_min, 1, MPI_DOUBLE, MPI_MIN, 0, MPI_COMM_WORLD);

    if (rank == 0) {
        // Na decomposição cíclica o Gatherv devolve as faixas empilhadas, não
        // na ordem das linhas. Reordena para que a imagem seja idêntica à do
        // baseline — sem isso, a validação elemento a elemento falharia mesmo
        // com o cálculo correto.
        if (ciclica) {
            std::vector<int> ordenada((size_t)largura * altura);
            for (int r = 0; r < nprocs; r++) {
                const int linhas_r = base + (r < resto ? 1 : 0);
                for (int j = 0; j < linhas_r; j++) {
                    const int destino = r + j * nprocs;
                    std::copy_n(imagem.data() + deslocamentos[r] + (size_t)j * largura,
                                largura, ordenada.data() + (size_t)destino * largura);
                }
            }
            imagem.swap(ordenada);
        }

        if (dump) {
            FILE* f = std::fopen(dump, "wb");
            if (!f) { std::perror("dump"); MPI_Abort(MPI_COMM_WORLD, 1); }
            std::fwrite(imagem.data(), sizeof(int), imagem.size(), f);
            std::fclose(f);
        }

        std::printf("versao=mpi config=%d decomposicao=%s largura=%d altura=%d max_iter=%d "
                    "checksum=%llu tempo=%.6f calculo=%.6f comunicacao=%.6f desbalanceamento=%.3f\n",
                    nprocs, nome_decomp, largura, altura, max_iter,
                    (unsigned long long)checksum, tempo, calc, comm,
                    calc_min > 0 ? calc / calc_min : 1.0);
    }

    MPI_Finalize();
    return 0;
}
