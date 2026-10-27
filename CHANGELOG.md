# Histórico de versões

## v1.0.3 — interface Português / English

- Botão com bandeiras no canto superior direito alterna os textos da interface, calibração, avisos e mensagens de diagnóstico imediatamente.
- Guarda a escolha em `settings.json`, sem alterar a calibração. A troca mantém a seleção atual e o controlador em execução.
- Bandeiras locais funcionam sem depender de emojis do Windows. Textos se ajustam à largura da janela nos dois idiomas.
- Preserva os detectores, atalhos e tempos da v1.0.2. O reconhecimento de relançamento continua usando a instrução visual do jogo em português.
- Instruções de uso também disponíveis em inglês em `README.en.md`.

Validação: 43 testes locais aprovados. Interface e executável conferidos em área gráfica isolada, com perfil vazio, nos dois idiomas e tamanhos de janela 1020×810 e 820×700. A seleção e o controlador simulado permanecem intactos ao alternar o idioma; não foi iniciada uma nova partida real para esta mudança de textos.

## v1.0.2 — estabilidade da raquete e do diagnóstico

- Os F10 novos confirmaram que o relançamento havia concluído. A falha posterior estava no acompanhamento: o recorte animado da raquete caiu abaixo do limite apesar de continuar visível.
- Preserva o caminho de comparação existente quando ele é válido; quando falha, tenta recuperar a posição pela faixa vermelha estreita do carrinho, conferindo tamanho e formato. Uma bota ausente continua sem gerar A/D.
- F10 salva uma cópia imutável em outra thread. Não solta A/D, não zera a velocidade e não reinicia a espera de relançamento durante o salvamento.
- Reduz a frequência da busca da instrução durante o jogo normal; uma instrução já visível continua sendo acompanhada a cada quadro.
- O foco exige o título do jogo, evitando confundir a janela do próprio assistente com o Dota. O diagnóstico inclui método da raquete, pontuações, motivo de perda, comando, alvo e tempo de processamento.

Validação: 36 testes, incluindo os três F10 novos, ausência real da bota, remoção da raquete, troca de poses com trajetória controlada e uma simulação completa do F10 preservando A/D. As capturas individuais não equivalem a uma partida contínua nova.

## v1.0.1 — reconhecimento de relançamento

- Corrige a espera por Espaço após uma pequena mudança de calibração: a instrução visível recebia 0,823 no reconhecimento anterior e era rejeitada pelo limite de 0,85.
- Compara traços claros suavizados em 13 escalas próximas, reduzindo a influência do cenário e da interpolação da imagem. O limite continua em 0,85.
- A captura real que falhou passou a ser reconhecida com pontuação aproximada de 0,937. O valor mede semelhança visual, não probabilidade de acerto.
- Acrescenta a captura e o histórico F10 como regressão, além de testes com pequenos deslocamentos e instrução parcial.
- Mostra a versão na janela e registra o método de reconhecimento nos diagnósticos.

Validação: 30 testes locais. Os quadros reais de jogo sem instrução permanecem negativos; a nova espera gera uma única solicitação de dois Espaços. A recepção das teclas pelo Dota na nova troca de nível depende de teste em jogo.

## v1.0.0

Primeira versão pública com interface, controle A/D, relançamento pela instrução visual e calibração embutida.
