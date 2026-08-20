# Ambiente de referência: Linux + g++ + OpenMPI (laboratório / Docker).
CXX      ?= g++
MPICXX   ?= mpic++
CXXFLAGS ?= -O2 -Wall -std=c++17
OMPFLAGS  = -fopenmp

# Reprodutibilidade bit-a-bit entre as três versões. Sem isto, seq/omp e mpi
# podem ser compilados por compiladores diferentes ($(CXX) x o compilador que o
# $(MPICXX) embrulha), que fundem `zr*zr - zi*zi + cr` em FMA de formas
# distintas — e pixels na fronteira de escape trocam de contagem de iteração,
# fazendo a validação de corretude falhar sem que haja erro de lógica.
# É flag de compilação, não alteração da lógica de cálculo.
FPFLAGS   = -ffp-contract=off

BIN = bin

all: $(BIN)/mandelbrot_seq $(BIN)/mandelbrot_omp $(BIN)/mandelbrot_mpi

seq: $(BIN)/mandelbrot_seq

$(BIN)/mandelbrot_seq: src/seq/mandelbrot_seq.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FPFLAGS) -o $@ $<

$(BIN)/mandelbrot_omp: src/openmp/mandelbrot_omp.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FPFLAGS) $(OMPFLAGS) -o $@ $<

$(BIN)/mandelbrot_mpi: src/mpi/mandelbrot_mpi.cpp | $(BIN)
	$(MPICXX) $(CXXFLAGS) $(FPFLAGS) -o $@ $<

# Build instrumentado para gprof (frente de perfilamento, Marco 1).
# Uso: make perfil && ./bin/mandelbrot_seq_prof 2000 2000 1000 && gprof ./bin/mandelbrot_seq_prof gmon.out | head -40
perfil: $(BIN)/mandelbrot_seq_prof

$(BIN)/mandelbrot_seq_prof: src/seq/mandelbrot_seq.cpp | $(BIN)
	$(CXX) $(CXXFLAGS) $(FPFLAGS) -pg -g -o $@ $<

$(BIN):
	mkdir -p $(BIN)

# Corretude: as três versões têm que produzir a MESMA matriz de iterações.
validar: all
	./scripts/validar.sh

# Campanha completa de medição + gráficos.
medir: all
	./scripts/medir.sh
	python3 scripts/graficos.py

clean:
	rm -rf $(BIN) gmon.out

.PHONY: all seq perfil validar medir clean
