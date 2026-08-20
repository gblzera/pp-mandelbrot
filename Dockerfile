# Ambiente equivalente ao laboratório da disciplina: Linux + g++ + OpenMPI.
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ make openmpi-bin libopenmpi-dev \
        python3 python3-matplotlib \
    && rm -rf /var/lib/apt/lists/*

# O mpirun do OpenMPI recusa rodar como root sem estas variáveis (padrão em contêiner).
ENV OMPI_ALLOW_RUN_AS_ROOT=1 \
    OMPI_ALLOW_RUN_AS_ROOT_CONFIRM=1

WORKDIR /projeto
CMD ["bash"]
