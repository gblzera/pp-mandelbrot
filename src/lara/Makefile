CXX = g++
MPICXX = mpicxx
CXXFLAGS = -O2 -std=c++17 -Wall -Wextra
.PHONY: all clean teste-local
all: sequencial openmp mpi hibrido
sequencial: sequencial.cpp comum.h
	$(CXX) $(CXXFLAGS) sequencial.cpp -o sequencial
openmp: openmp.cpp comum.h
	$(CXX) $(CXXFLAGS) -fopenmp openmp.cpp -o openmp
mpi: mpi.cpp mpi_comum.h comum.h
	$(MPICXX) $(CXXFLAGS) mpi.cpp -o mpi
hibrido: hibrido.cpp mpi_comum.h comum.h
	$(MPICXX) $(CXXFLAGS) -fopenmp hibrido.cpp -o hibrido
teste-local: sequencial openmp
	./sequencial 400 600 1000
	./openmp 400 600 1000 todos 4 16
	./openmp 400 600 1000 coordenador 4 16
clean:
	rm -f sequencial openmp mpi hibrido
