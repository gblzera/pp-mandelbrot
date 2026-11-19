#include "comum.h"
#include <iostream>
int main(int argc, char** argv) {
    try {
        const Config c = ler_config(argc, argv);
        std::vector<int> imagem((size_t)c.largura * c.altura);
        const double inicio = relogio();
        for (int y = 0; y < c.altura; ++y)
            for (int x = 0; x < c.largura; ++x)
                imagem[(size_t)y*c.largura+x] = calcular_pixel(x,y,c);
        const double tempo = relogio()-inicio;
        imprimir("sequencial","unico",c,1,checksum_imagem(imagem),tempo,tempo,0,1);
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
