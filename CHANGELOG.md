# Histórico de versões

## v1.0.1 — reconhecimento de relançamento

- Corrige a espera por Espaço após uma pequena mudança de calibração: a instrução visível recebia 0,823 no reconhecimento anterior e era rejeitada pelo limite de 0,85.
- Compara traços claros suavizados em 13 escalas próximas, reduzindo a influência do cenário e da interpolação da imagem. O limite continua em 0,85.
- A captura real que falhou passou a ser reconhecida com pontuação aproximada de 0,937. O valor mede semelhança visual, não probabilidade de acerto.
- Acrescenta a captura e o histórico F10 como regressão, além de testes com pequenos deslocamentos e instrução parcial.
- Mostra a versão na janela e registra o método de reconhecimento nos diagnósticos.

Validação: 30 testes locais. Os quadros reais de jogo sem instrução permanecem negativos; a nova espera gera uma única solicitação de dois Espaços. A recepção das teclas pelo Dota na nova troca de nível depende de teste em jogo.

## v1.0.0

Primeira versão pública com interface, controle A/D, relançamento pela instrução visual e calibração embutida.
