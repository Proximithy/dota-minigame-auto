# Dota Minigame Auto • primeira versão pública

Um projeto que começou com um vídeo de um minigame e virou um aplicativo para Windows.

Ele acompanha a bota no quebra-blocos do Dark Carnival, move o carrinho com A/D e reconhece a instrução da troca de nível para apertar Espaço duas vezes. Tudo com processamento local de imagem e uma interface simples.

## Download

Baixe **Dota-Minigame-Auto-Calibrado.exe** nos arquivos desta release. É um executável único, com as dependências e a calibração de referência embutidas.

**F7** inicia · **F8** pausa/retoma · **F9** para · **F10** salva diagnóstico.

Se a resolução ou a posição da janela forem diferentes, use **Calibrar** antes de jogar. O Dota precisa estar em primeiro plano para receber os comandos.

## Nesta versão

- Interface com calibração e modo de observação.
- Detecção da bota e da faixa estável do carrinho com OpenCV.
- Previsão de rebotes laterais e controle A/D.
- Relançamento pela instrução “TRAVAR POSIÇÃO DO CARRINHO”.
- Calibração embutida, com preferência por recalibrações locais.
- Código-fonte sob MIT e testes incluídos no repositório.

O funcionamento foi confirmado pelo autor na configuração de referência. Outras resoluções, idiomas e efeitos ainda podem exigir ajustes. Não há garantia de vitória ou pontuação.

Veja o README para instruções completas e os avisos de componentes em THIRD_PARTY_NOTICES.md e licenses/.
