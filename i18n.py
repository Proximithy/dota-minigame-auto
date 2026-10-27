"""UI messages and a language preference independent of calibration/game state."""
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import tkinter as tk

LANGUAGES = ('pt-BR', 'en')

# Portuguese is the source catalog so existing diagnostic reason strings remain stable.
EN = {
    'Assistente do Minigame': 'Minigame Assistant',
    'Calibre na imagem, confira a detecção e depois ative A/D.': 'Calibrate on the image, check detection, then enable A/D controls.',
    '1. Calibrar': '1. Calibrate',
    '2. Testar (F6)': '2. Preview (F6)',
    '3. Jogar (F7)': '3. Play (F7)',
    'Parar (F9)': 'Stop (F9)',
    'Comece em “Calibrar”. O aplicativo inicia parado.': 'Start with “Calibrate”. The application starts stopped.',
    'Após calibrar, volte ao Dota e aperte F7 para jogar, sem sair do minigame.': 'After calibration, return to Dota and press F7 to play without leaving the minigame.',
    'Confirmar seleção': 'Confirm selection',
    'Cancelar calibração': 'Cancel calibration',
    'Relançar após troca de nível (Espaço 2×)': 'Relaunch after level change (Space ×2)',
    'No Dota: F6 testa • F7 joga • F8 pausa/retoma • F9 para • F10 salva diagnóstico\nInstrução “Travar posição do carrinho” detectada: Espaço 2×, uma vez por espera.':
        'In Dota: F6 previews • F7 plays • F8 pauses/resumes • F9 stops • F10 saves diagnostics\nPortuguese “Travar posição do carrinho” prompt detected: Space ×2, once per wait.',
    'Sua calibração embutida foi carregada. Recalibre se a janela ou resolução mudou.': 'Bundled calibration loaded. Recalibrate if the window or resolution has changed.',
    'Calibração anterior carregada. Recalibre se a janela ou resolução mudou.': 'Saved calibration loaded. Recalibrate if the window or resolution has changed.',
    'Pare o teste antes de recalibrar.': 'Stop the preview before recalibrating.',
    'Volte ao Dota. Captura em 5 segundos; o aplicativo vai se esconder.': 'Return to Dota. Capturing in 5 seconds; this window will hide.',
    'Deixe o Dota 2 em primeiro plano durante os 5 segundos e tente novamente.': 'Keep Dota 2 in the foreground during the 5-second countdown and try again.',
    'Não foi possível capturar': 'Unable to capture',
    '1/3 — Arraste um retângulo no INTERIOR da arena, até as paredes. Deixe a decoração de fora.': '1/3 — Drag a rectangle INSIDE the arena, up to its walls. Exclude the decorations.',
    '2/3 — Arraste um retângulo justo em volta da BOLA, com pouca margem.': '2/3 — Drag a tight rectangle around the BALL, with little margin.',
    '3/3 — Arraste um retângulo em volta da RAQUETE inteira, com pouca margem.': '3/3 — Drag a rectangle around the entire PADDLE, with little margin.',
    'A imagem está congelada. Arraste com o mouse e clique em “Confirmar seleção”.': 'The image is frozen. Drag with the mouse, then click “Confirm selection”.',
    'Arena pequena': 'Arena too small',
    'Marque toda a área onde a bola circula.': 'Select the entire area where the ball moves.',
    'A bola precisa estar acima da raquete na captura. Refaça a captura antes do lançamento.': 'The ball must be above the paddle in the capture. Capture again before launching.',
    'O detector não reconheceu a bola no recorte escolhido. Cancele e capture novamente com a bola bem visível.': 'The detector could not recognize the ball in this crop. Cancel and capture again with the ball clearly visible.',
    'O detector encontrou outra raquete. Marque novamente o carrinho inteiro, com pouca margem.': 'The detector found a different paddle. Select the entire cart again, with little margin.',
    'Calibração salva. Volte ao Dota: F6 testa sem teclas; F7 inicia o controle.': 'Calibration saved. Return to Dota: F6 previews without inputs; F7 starts controls.',
    'Na prévia: retângulos marcam bola e raquete; o círculo azul indica o alvo.': 'Preview: rectangles mark the ball and paddle; the blue circle shows the target.',
    'Revise os recortes': 'Review the selected crops',
    'Calibração cancelada. A anterior continua disponível, se houver.': 'Calibration cancelled. Your previous calibration remains available, if any.',
    'Calibre primeiro': 'Calibrate first',
    'Clique em “1. Calibrar” para marcar a arena, a bola e a raquete.': 'Click “1. Calibrate” to select the arena, ball and paddle.',
    'Volte ao Dota. Modo observação: sem apertar teclas.': 'Return to Dota. Preview mode: no key inputs.',
    'Volte ao Dota. Controle A/D ativo somente no Dota. F9 para.': 'Return to Dota. A/D controls are active only in Dota. F9 stops.',
    'F8 pausa/retoma; F9 para. Use F6/F7 dentro do Dota para iniciar sem Alt+Tab.': 'F8 pauses/resumes; F9 stops. Use F6/F7 inside Dota to start without Alt+Tab.',
    'Pausado (F8 retoma).': 'Paused (F8 resumes).',
    'Aguardando você voltar ao Dota 2. Teclas soltas.': 'Waiting for you to return to Dota 2. Keys released.',
    'Instrução de lançamento: Espaço enviado duas vezes.': 'Launch prompt: Space sent twice.',
    'Relançamento interrompido; teclas soltas.': 'Relaunch interrupted; keys released.',
    'Detectando • raquete recuperada pela faixa vermelha': 'Tracking • paddle recovered using the red stripe',
    'Detectando': 'Tracking',
    'Raquete não reconhecida — A/D soltos': 'Paddle not recognized — A/D released',
    'Bota não reconhecida — A/D soltos': 'Boot not recognized — A/D released',
    'Salto de detecção rejeitado — A/D soltos': 'Detection jump rejected — A/D released',
    'Aguardando detecção — A/D soltos': 'Waiting for detection — A/D released',
    '{state} • Bola {ball:.0%} • Raquete {paddle:.0%} • {mode}': '{state} • Ball {ball:.0%} • Paddle {paddle:.0%} • {mode}',
    'Observação': 'Preview',
    'Controle A/D': 'A/D controls',
    'Erro: {error}': 'Error: {error}',
    'Parando e soltando as teclas…': 'Stopping and releasing keys…',
    'Parado.': 'Stopped.',
    'Calibre primeiro na interface. Depois volte ao Dota e aperte F7.': 'Calibrate in the application first. Then return to Dota and press F7.',
    'Parado. Dentro do Dota: F6 testa sem teclas; F7 inicia o controle.': 'Stopped. In Dota: F6 previews without inputs; F7 starts controls.',
    'Teste isolado: interface, prévia, seleção e detecção aprovados.': 'Isolated check: interface, preview, selection and tracking passed.',
    'Diagnóstico salvo em {folder}': 'Diagnostics saved to {folder}',
    'Erro ao salvar diagnóstico: {error}': 'Unable to save diagnostics: {error}',
    'Referência de relançamento ausente no aplicativo.': 'The application is missing its relaunch reference image.',
    'Recorte sem detalhe. Marque novamente a bola e a raquete.': 'The crop has too little detail. Select the ball and paddle again.',
    'O recorte não cabe na arena. Refaça a calibração.': 'The crop does not fit inside the arena. Calibrate again.',
    'aguardando instrução de lançamento': 'waiting for launch prompt',
    'relançamento desativado/observação': 'relaunch disabled / preview mode',
    'Espaços já enviados; aguardando a instrução desaparecer': 'Space inputs already sent; waiting for the prompt to disappear',
    'instrução de lançamento não visível': 'launch prompt not visible',
    'aguardando raquete reconhecida': 'waiting for paddle recognition',
    'Instrução de lançamento detectada: {elapsed}/{dwell}s': 'Launch prompt detected: {elapsed}/{dwell}s',
    'enviar dois Espaços pela instrução de lançamento': 'send Space twice in response to the launch prompt',
    'Não foi possível salvar o idioma: {error}': 'Unable to save language preference: {error}',
}


@dataclass(frozen=True)
class Message:
    key: str
    values: dict = field(default_factory=dict)


def message(key, **values):
    return Message(key, values)


def translate(language, value):
    if isinstance(value, Message):
        template = EN.get(value.key, value.key) if language == 'en' else value.key
        return template.format(**{k: translate(language, v) if isinstance(v, (Message, str)) else v
                                  for k, v in value.values.items()})
    if language == 'en':
        # The launch detector keeps its original reasons for diagnostic compatibility.
        match = re.fullmatch(r'Instrução de lançamento detectada: ([\d.]+)/([\d.]+)s', value)
        if match:
            return translate(language, message('Instrução de lançamento detectada: {elapsed}/{dwell}s',
                                              elapsed=match[1], dwell=match[2]))
        return EN.get(value, value)
    return value


class LocalizedVar(tk.StringVar):
    """Retain the message so a live language change can render it again."""
    def __init__(self, master, language, value):
        self.language = language
        super().__init__(master)
        self.set(value)

    def set(self, value):
        self.message = value
        super().set(translate(self.language(), value))

    def refresh(self):
        self.set(self.message)


def load_language(folder):
    try:
        settings = json.loads((Path(folder) / 'settings.json').read_text(encoding='utf-8'))
        language = settings.get('language')
        return language if language in LANGUAGES else 'pt-BR'
    except (OSError, ValueError, AttributeError):
        return 'pt-BR'


def save_language(folder, language):
    if language not in LANGUAGES:
        raise ValueError('Unsupported language')
    folder = Path(folder)
    path = folder / 'settings.json'
    try:
        settings = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(settings, dict): settings = {}
    except (OSError, ValueError):
        settings = {}
    settings['language'] = language
    folder.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def flag_image(language):
    """Small local icons, independent of the Windows emoji font."""
    from PIL import Image, ImageDraw
    image = Image.new('RGB', (72, 48), '#009b3a' if language == 'pt-BR' else 'white')
    draw = ImageDraw.Draw(image)
    if language == 'pt-BR':
        draw.polygon([(36, 4), (67, 24), (36, 44), (5, 24)], fill='#ffdf00')
        draw.ellipse((23, 11, 49, 37), fill='#002776')
        draw.arc((19, 23, 53, 43), 202, 327, fill='white', width=3)
    else:
        for stripe in range(0, 13, 2):
            draw.rectangle((0, round(stripe*48/13), 71, round((stripe+1)*48/13)-1), fill='#b22234')
        draw.rectangle((0, 0, 30, 25), fill='#3c3b6e')
        for row in range(5):
            for column in range(6):
                draw.ellipse((3+column*4, 3+row*4, 4+column*4, 4+row*4), fill='white')
    return image.resize((30, 20), Image.Resampling.LANCZOS)
