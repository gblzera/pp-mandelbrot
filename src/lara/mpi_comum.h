#pragma once
#include "comum.h"
#include <mpi.h>
#include <numeric>
#include <iostream>
#ifdef _OPENMP
#include <omp.h>
#endif

// Cada processo recebe uma lista de LINHAS GLOBAIS. Cada linha e uma tarefa.
// Estrategia bloco: linhas consecutivas; ciclica: linhas intercaladas.
// Modo mestre: rank 0 distribui listas e NAO calcula.
// Modo todos: todos os ranks calculam, inclusive rank 0.
inline std::vector<int> linhas_do_rank(int trabalhador, int trabalhadores,
                                       int altura, bool ciclica) {
    std::vector<int> linhas;
    if (ciclica) {
        for (int y=trabalhador; y<altura; y+=trabalhadores) linhas.push_back(y);
    } else {
        int base=altura/trabalhadores, resto=altura%trabalhadores;
        int inicio=trabalhador*base+std::min(trabalhador,resto);
        int qtd=base+(trabalhador<resto?1:0);
        for (int y=inicio;y<inicio+qtd;++y) linhas.push_back(y);
    }
    return linhas;
}
inline int executar_mpi(int argc, char** argv, bool hibrido) {
    int fornecido=0;
    // Somente a thread principal faz chamadas MPI (FUNNELED).
    MPI_Init_thread(&argc,&argv,MPI_THREAD_FUNNELED,&fornecido);
    int rank=0,nprocs=0;
    MPI_Comm_rank(MPI_COMM_WORLD,&rank);
    MPI_Comm_size(MPI_COMM_WORLD,&nprocs);
    int erro=0;
    Config c;
    std::string modo, decomp;
    int threads=1,chunk=16;
    try {
        c=ler_config(argc,argv);
        modo=argc>4?argv[4]:"todos";
        decomp=argc>5?argv[5]:"ciclica";
        threads=argc>6?std::atoi(argv[6]):2;
        chunk=argc>7?std::atoi(argv[7]):16;
        if ((modo!="todos"&&modo!="mestre") ||
            (decomp!="bloco"&&decomp!="ciclica") ||
            (modo=="mestre"&&nprocs<2) || threads<1 || chunk<1 ||
            (hibrido&&fornecido<MPI_THREAD_FUNNELED))
            throw std::runtime_error("Argumentos invalidos ou MPI sem suporte FUNNELED");
    } catch (const std::exception& e) { erro=1; if(rank==0) std::cerr<<e.what()<<'\n'; }
    int algum_erro=0;
    MPI_Allreduce(&erro,&algum_erro,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    if (algum_erro) { MPI_Finalize(); return 1; }
    const bool mestre=(modo=="mestre");
    const bool ciclica=(decomp=="ciclica");
    const int trabalhadores=nprocs-(mestre?1:0);
    std::vector<int> linhas;
    MPI_Barrier(MPI_COMM_WORLD);
    double t0=MPI_Wtime();
    if (mestre) {
        if (rank==0) {
            // Distribui a lista de linhas: rank 1 recebe trabalhador 0, etc.
            for (int r=1;r<nprocs;++r) {
                auto lista=linhas_do_rank(r-1,trabalhadores,c.altura,ciclica);
                int qtd=(int)lista.size();
                MPI_Send(&qtd,1,MPI_INT,r,10,MPI_COMM_WORLD);
                if(qtd) MPI_Send(lista.data(),qtd,MPI_INT,r,11,MPI_COMM_WORLD);
            }
        } else {
            int qtd=0;
            MPI_Recv(&qtd,1,MPI_INT,0,10,MPI_COMM_WORLD,MPI_STATUS_IGNORE);
            linhas.resize(qtd);
            if(qtd) MPI_Recv(linhas.data(),qtd,MPI_INT,0,11,MPI_COMM_WORLD,MPI_STATUS_IGNORE);
        }
    } else {
        // Todos calculam; a divisao e deterministica, sem mensagens de tarefas.
        linhas=linhas_do_rank(rank,trabalhadores,c.altura,ciclica);
    }
    double t_inicio_calc=MPI_Wtime();
    std::vector<int> faixa((size_t)linhas.size()*c.largura);
    if (hibrido) {
#ifdef _OPENMP
        // Indices distintos => nenhuma corrida em faixa. j e x sao privados.
        omp_set_schedule(omp_sched_dynamic,chunk);
        #pragma omp parallel for collapse(2) schedule(runtime) num_threads(threads)
        for (int j=0;j<(int)linhas.size();++j)
            for (int x=0;x<c.largura;++x)
                faixa[(size_t)j*c.largura+x]=calcular_pixel(x,linhas[j],c);
#else
        if(rank==0) std::cerr<<"Compilar hibrido com -fopenmp\n";
        MPI_Abort(MPI_COMM_WORLD,2);
#endif
    } else {
        for (int j=0;j<(int)linhas.size();++j)
            for (int x=0;x<c.largura;++x)
                faixa[(size_t)j*c.largura+x]=calcular_pixel(x,linhas[j],c);
    }
    const double t_fim_calc=MPI_Wtime();
    // Gatherv recolhe faixas; os tamanhos podem diferir entre ranks.
    int qtd=(int)faixa.size();
    std::vector<int> contagens(nprocs),deslocamentos(nprocs);
    MPI_Gather(&qtd,1,MPI_INT,rank==0?contagens.data():nullptr,1,MPI_INT,0,MPI_COMM_WORLD);
    std::vector<int> empilhada;
    if(rank==0) {
        int total=0;
        for(int r=0;r<nprocs;++r) { deslocamentos[r]=total;total+=contagens[r]; }
        empilhada.resize(total);
    }
    MPI_Gatherv(faixa.data(),qtd,MPI_INT,
                rank==0?empilhada.data():nullptr,
                rank==0?contagens.data():nullptr,
                rank==0?deslocamentos.data():nullptr,MPI_INT,0,MPI_COMM_WORLD);
    // Medicao da comunicacao inclui envio de tarefas + coleta dos resultados,
    // e pode incluir esperas por ranks mais lentos.
    const double t_fim_com=MPI_Wtime();
    double calc_local=t_fim_calc-t_inicio_calc;
    double comm_local=(t_inicio_calc-t0)+(t_fim_com-t_fim_calc);
    double total_local=t_fim_com-t0;
    double calc_max=0,calc_min=0,comm_max=0,total_max=0;
    // Exclui o mestre do MIN dos calculadores (senao daria quase zero).
    double calc_min_valida=(mestre&&rank==0)?1e100:calc_local;
    MPI_Reduce(&calc_local,&calc_max,1,MPI_DOUBLE,MPI_MAX,0,MPI_COMM_WORLD);
    MPI_Reduce(&calc_min_valida,&calc_min,1,MPI_DOUBLE,MPI_MIN,0,MPI_COMM_WORLD);
    MPI_Reduce(&comm_local,&comm_max,1,MPI_DOUBLE,MPI_MAX,0,MPI_COMM_WORLD);
    MPI_Reduce(&total_local,&total_max,1,MPI_DOUBLE,MPI_MAX,0,MPI_COMM_WORLD);
    if(rank==0) {
        std::vector<int> imagem((size_t)c.largura*c.altura);
        // Reconstroi ordem original mesmo para decomposicao ciclica.
        for(int r=(mestre?1:0);r<nprocs;++r) {
            auto lista=linhas_do_rank(r-(mestre?1:0),trabalhadores,c.altura,ciclica);
            for(size_t j=0;j<lista.size();++j)
                std::copy_n(empilhada.data()+deslocamentos[r]+j*c.largura,
                            c.largura,imagem.data()+(size_t)lista[j]*c.largura);
        }
        imprimir(hibrido?"hibrido":"mpi",(modo+"_"+decomp).c_str(),c,
                nprocs,checksum_imagem(imagem),total_max,calc_max,comm_max,
                calc_min>0?calc_max/calc_min:0);
    }
    MPI_Finalize();
    return 0;
}
