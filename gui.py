"""Native Windows GUI. Calibration and previews stay inside the application."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

import cv2
import mss
import numpy as np
from PIL import Image, ImageTk
from tracker import Tracker
from auto_launch import double_space
from launch_prompt import LaunchPrompt
from calibration import load_calibration
from diagnostics import DiagnosticWriter
from i18n import LocalizedVar, flag_image, load_language, message, save_language, translate

USER = ctypes.WinDLL('user32', use_last_error=True)
USER.SetProcessDPIAware()
USER.GetForegroundWindow.restype = wintypes.HWND
USER.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
USER.GetAsyncKeyState.argtypes = [ctypes.c_int]
USER.GetAsyncKeyState.restype = ctypes.c_short
USER.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_size_t]
DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'DotaMinigameAssistente'
APP_VERSION = '1.0.3'


def is_dota_title(title):
    return title.strip().casefold()=='dota 2'


def dota_focused():
    title = ctypes.create_unicode_buffer(512)
    USER.GetWindowTextW(USER.GetForegroundWindow(), title, 512)
    return is_dota_title(title.value)


def snapshot_window(root, output):
    """Print only our window, including on a private Windows desktop."""
    gdi = ctypes.WinDLL('gdi32', use_last_error=True)
    USER.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    USER.GetAncestor.restype = wintypes.HWND
    USER.GetWindowDC.argtypes = [wintypes.HWND]
    USER.GetWindowDC.restype = wintypes.HDC
    USER.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    USER.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    USER.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi.CreateCompatibleDC.restype = wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = wintypes.HANDLE
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
    gdi.SelectObject.restype = wintypes.HANDLE
    gdi.GetBitmapBits.argtypes = [wintypes.HANDLE, wintypes.LONG, ctypes.c_void_p]
    gdi.DeleteObject.argtypes = [wintypes.HANDLE]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    hwnd = USER.GetAncestor(root.winfo_id(), 2)
    rect = wintypes.RECT()
    USER.GetWindowRect(hwnd, ctypes.byref(rect))
    width, height = rect.right-rect.left, rect.bottom-rect.top
    dc = USER.GetWindowDC(hwnd)
    memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        if not USER.PrintWindow(hwnd, memory, 2):
            raise RuntimeError('PrintWindow failed')
        buffer = ctypes.create_string_buffer(width*height*4)
        if gdi.GetBitmapBits(bitmap, len(buffer), buffer) != len(buffer):
            raise RuntimeError('Bitmap read failed')
        Image.frombytes('RGB', (width, height), buffer.raw, 'raw', 'BGRX').save(output)
    finally:
        gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        USER.ReleaseDC(hwnd, dc)


class App:
    def __init__(self, root):
        self.root = root
        self.stop = threading.Event()
        self.worker = None
        self.diagnostic_writer=DiagnosticWriter()
        self.messages = queue.Queue(maxsize=2)
        self.config = None
        self.ball = self.paddle = None
        self.photo = None
        self.stage = None
        self.selection = None
        self.box_id = None
        self.countdown = None
        self.hotkeys_down = set()
        self.closing = False
        self.testing = '--self-test' in sys.argv
        self.auto_launch_enabled = True
        self.language = load_language(DATA)
        self.localized_vars = []
        root.geometry('1020x810')
        root.minsize(820, 700)
        root.configure(bg='#171b24')
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#171b24')
        style.configure('TLabel', background='#171b24', foreground='#e8edf5', font=('Segoe UI', 11))
        style.configure('TButton', font=('Segoe UI', 10), padding=9)
        style.configure('TCheckbutton', background='#171b24', foreground='#e8edf5', font=('Segoe UI', 10))
        style.map('TCheckbutton', background=[('active', '#171b24')])
        style.configure('Title.TLabel', font=('Segoe UI', 21, 'bold'))
        body = ttk.Frame(root, padding=20)
        body.pack(fill='both', expand=True)
        header = ttk.Frame(body)
        header.pack(fill='x')
        ttk.Label(header, textvariable=self.text('Assistente do Minigame'), style='Title.TLabel').pack(side='left')
        self.flags = {language: ImageTk.PhotoImage(flag_image(language), master=root) for language in ('pt-BR', 'en')}
        self.language_button = ttk.Button(header, command=self.toggle_language, compound='left')
        self.language_button.pack(side='right')
        ttk.Label(body, textvariable=self.text('Calibre na imagem, confira a detecção e depois ative A/D.')).pack(anchor='w', pady=(4, 14))
        bar = ttk.Frame(body)
        bar.pack(fill='x')
        self.calibrate_button = ttk.Button(bar, textvariable=self.text('1. Calibrar'), command=self.capture_start)
        self.calibrate_button.pack(side='left', padx=(0, 8))
        self.observe_button = ttk.Button(bar, textvariable=self.text('2. Testar (F6)'), command=lambda: self.start(True))
        self.observe_button.pack(side='left', padx=(0, 8))
        self.play_button = ttk.Button(bar, textvariable=self.text('3. Jogar (F7)'), command=lambda: self.start(False))
        self.play_button.pack(side='left', padx=(0, 8))
        ttk.Button(bar, textvariable=self.text('Parar (F9)'), command=self.halt).pack(side='left')
        self.status = self.text('Comece em “Calibrar”. O aplicativo inicia parado.')
        ttk.Label(body, textvariable=self.status, wraplength=950).pack(anchor='w', pady=(14, 6))
        self.instruction = self.text('Após calibrar, volte ao Dota e aperte F7 para jogar, sem sair do minigame.')
        ttk.Label(body, textvariable=self.instruction, wraplength=950).pack(anchor='w', pady=(0, 8))
        self.canvas = tk.Canvas(body, width=950, height=200, bg='#0c1017', highlightthickness=1, highlightbackground='#394454')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag_move)
        self.canvas.bind('<ButtonRelease-1>', self.drag_end)
        footer = ttk.Frame(body)
        footer.pack(fill='x', pady=(10, 0))
        self.confirm_button = ttk.Button(footer, textvariable=self.text('Confirmar seleção'), command=self.confirm, state='disabled')
        self.confirm_button.pack(side='left')
        ttk.Button(footer, textvariable=self.text('Cancelar calibração'), command=self.cancel_calibration).pack(side='left', padx=8)
        self.auto_launch_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(body, textvariable=self.text('Relançar após troca de nível (Espaço 2×)'), variable=self.auto_launch_var,
                        command=lambda: setattr(self, 'auto_launch_enabled', self.auto_launch_var.get())).pack(anchor='w', pady=(6, 0))
        ttk.Label(body, textvariable=self.text('No Dota: F6 testa • F7 joga • F8 pausa/retoma • F9 para • F10 salva diagnóstico\n'
                  'Instrução “Travar posição do carrinho” detectada: Espaço 2×, uma vez por espera.'), wraplength=950).pack(anchor='w', pady=(10, 0))
        body.bind('<Configure>', lambda event: self.wrap_labels(body, event.width-40))
        self.apply_language()
        self.load()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(80, self.poll)

    def text(self, value):
        variable = LocalizedVar(self.root, lambda: self.language, value)
        self.localized_vars.append(variable)
        return variable

    def tr(self, value):
        return translate(self.language, value)

    def apply_language(self):
        self.root.title(f'{self.tr("Assistente do Minigame")} • Dota 2 • v{APP_VERSION}')
        target = 'en' if self.language == 'pt-BR' else 'pt-BR'
        self.language_button.configure(text='English' if target == 'en' else 'Português', image=self.flags[target])
        for variable in self.localized_vars:
            variable.refresh()

    def toggle_language(self):
        self.language = 'en' if self.language == 'pt-BR' else 'pt-BR'
        self.apply_language()
        try:
            save_language(DATA, self.language)
        except OSError as exc:
            messagebox.showerror(self.tr('Erro: {error}').format(error=''),
                                 self.tr(message('Não foi possível salvar o idioma: {error}', error=str(exc))))

    @staticmethod
    def wrap_labels(body, width):
        for widget in body.winfo_children():
            if isinstance(widget, ttk.Label):
                widget.configure(wraplength=max(300, width))

    def load(self):
        embedded=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'default_calibration'
        result=load_calibration(DATA,embedded)
        self.calibration_source=None
        if result is None:
            self.config = None
            return
        self.config,self.ball,self.paddle,self.calibration_source=result
        self.status.set(('Sua calibração embutida foi carregada.' if self.calibration_source=='embedded'
                         else 'Calibração anterior carregada.')+' Recalibre se a janela ou resolução mudou.')

    def show(self, frame):
        self.canvas.delete('all')
        self.scale = min(max(100, self.canvas.winfo_width()-4)/frame.shape[1],
                         max(100, self.canvas.winfo_height()-4)/frame.shape[0])
        size = (max(1, int(frame.shape[1]*self.scale)), max(1, int(frame.shape[0]*self.scale)))
        image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).resize(size, Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, image=self.photo, anchor='nw')
        self.display_width, self.display_height = size

    def busy(self, value):
        for button in [self.calibrate_button, self.observe_button, self.play_button]:
            button.configure(state='disabled' if value else 'normal')

    def capture_start(self):
        if self.worker and self.worker.is_alive():
            self.status.set('Pare o teste antes de recalibrar.')
            return
        self.busy(True)
        self.status.set('Volte ao Dota. Captura em 5 segundos; o aplicativo vai se esconder.')
        self.root.withdraw()
        self.countdown = self.root.after(5000, self.capture)

    def capture(self):
        self.countdown = None
        try:
            if not dota_focused():
                raise ValueError('Deixe o Dota 2 em primeiro plano durante os 5 segundos e tente novamente.')
            with mss.MSS() as screen:
                self.monitor = dict(screen.monitors[0])
                self.full_frame = np.asarray(screen.grab(self.monitor))[:, :, :3].copy()
            self.stage = 0
            self.current_frame = self.full_frame
            self.root.deiconify()
            self.root.update_idletasks()
            self.set_stage()
        except Exception as exc:
            self.root.deiconify()
            self.busy(False)
            messagebox.showerror(self.tr('Não foi possível capturar'), self.tr(str(exc)))

    def set_stage(self):
        self.selection = None
        self.box_id = None
        self.confirm_button.configure(state='disabled')
        text = ['1/3 — Arraste um retângulo no INTERIOR da arena, até as paredes. Deixe a decoração de fora.',
                '2/3 — Arraste um retângulo justo em volta da BOLA, com pouca margem.',
                '3/3 — Arraste um retângulo em volta da RAQUETE inteira, com pouca margem.'][self.stage]
        self.status.set(text)
        self.instruction.set('A imagem está congelada. Arraste com o mouse e clique em “Confirmar seleção”.')
        self.show(self.current_frame)

    def point(self, event):
        return (min(max(event.x, 0), self.display_width), min(max(event.y, 0), self.display_height))

    def drag_start(self, event):
        if self.stage is None:
            return
        self.origin = self.point(event)
        if self.box_id:
            self.canvas.delete(self.box_id)
        x, y = self.origin
        self.box_id = self.canvas.create_rectangle(x, y, x, y, outline='#51d9a0', width=2)
        self.selection = None
        self.confirm_button.configure(state='disabled')

    def drag_move(self, event):
        if self.stage is not None and self.box_id:
            self.canvas.coords(self.box_id, *self.origin, *self.point(event))

    def drag_end(self, event):
        if self.stage is None or not self.box_id:
            return
        self.drag_move(event)
        x1, y1 = self.origin
        x2, y2 = self.point(event)
        x, y = int(min(x1, x2)/self.scale), int(min(y1, y2)/self.scale)
        right, bottom = int(max(x1, x2)/self.scale), int(max(y1, y2)/self.scale)
        right, bottom = min(right, self.current_frame.shape[1]), min(bottom, self.current_frame.shape[0])
        self.selection = (x, y, right-x, bottom-y)
        self.confirm_button.configure(state='normal' if min(right-x, bottom-y) >= 4 else 'disabled')

    def confirm(self):
        if self.stage is None or not self.selection:
            return
        x, y, w, h = self.selection
        if self.stage == 0:
            if w < 80 or h < 80:
                messagebox.showinfo(self.tr('Arena pequena'), self.tr('Marque toda a área onde a bola circula.'))
                return
            self.arena_box = self.selection
            self.arena_frame = self.full_frame[y:y+h, x:x+w].copy()
            self.current_frame = self.arena_frame
            self.stage = 1
            self.set_stage()
        elif self.stage == 1:
            self.pending_ball_box = self.selection
            self.pending_ball = self.arena_frame[y:y+h, x:x+w].copy()
            self.stage = 2
            self.set_stage()
        else:
            try:
                bx, by, bw, bh = self.pending_ball_box
                if by+bh >= y+h:
                    raise ValueError('A bola precisa estar acima da raquete na captura. Refaça a captura antes do lançamento.')
                ax, ay, aw, ah = self.arena_box
                paddle = self.arena_frame[y:y+h, x:x+w].copy()
                config = {'arena': {'left': self.monitor['left']+ax, 'top': self.monitor['top']+ay,
                                    'width': aw, 'height': ah}, 'paddle_y': y,
                          'paddle_band': max(h*2, 30), 'deadzone': max(5, w*.18),
                          'threshold_ball': .60, 'threshold_paddle': .70}
                detector = Tracker(config, self.pending_ball, paddle)
                verified, _, valid, bs, ps = detector.step(self.arena_frame, time.perf_counter())
                dx, dy, dw, dh = detector.ball_box
                if not valid or not (bx-8 <= dx+dw/2 <= bx+bw+8 and by-8 <= dy+dh/2 <= by+bh+8):
                    raise ValueError('O detector não reconheceu a bola no recorte escolhido. Cancele e capture novamente com a bola bem visível.')
                dx, dy, dw, dh = detector.paddle_box
                if not (x-8 <= dx+dw/2 <= x+w+8 and y-8 <= dy+dh/2 <= y+h+8):
                    raise ValueError('O detector encontrou outra raquete. Marque novamente o carrinho inteiro, com pouca margem.')
                DATA.mkdir(parents=True, exist_ok=True)
                for name, frame in [('ball', self.pending_ball), ('paddle', paddle)]:
                    (DATA/f'{name}.png').write_bytes(cv2.imencode('.png', frame)[1].tobytes())
                (DATA/'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
                self.config, self.ball, self.paddle = config, self.pending_ball, paddle
                self.stage = None
                self.confirm_button.configure(state='disabled')
                self.busy(False)
                self.status.set('Calibração salva. Volte ao Dota: F6 testa sem teclas; F7 inicia o controle.')
                self.instruction.set('Na prévia: retângulos marcam bola e raquete; o círculo azul indica o alvo.')
                self.show(verified)
            except Exception as exc:
                messagebox.showerror(self.tr('Revise os recortes'), self.tr(str(exc)))

    def cancel_calibration(self):
        if self.countdown:
            self.root.after_cancel(self.countdown)
            self.countdown = None
            self.root.deiconify()
        if self.stage is not None:
            self.stage = None
            self.confirm_button.configure(state='disabled')
            self.status.set('Calibração cancelada. A anterior continua disponível, se houver.')
            self.busy(False)

    def start(self, observe):
        if self.worker and self.worker.is_alive():
            return
        if not self.config:
            messagebox.showinfo(self.tr('Calibre primeiro'), self.tr('Clique em “1. Calibrar” para marcar a arena, a bola e a raquete.'))
            return
        self.stop.clear()
        self.busy(True)
        self.status.set('Volte ao Dota. ' + ('Modo observação: sem apertar teclas.' if observe else 'Controle A/D ativo somente no Dota. F9 para.'))
        self.instruction.set('F8 pausa/retoma; F9 para. Use F6/F7 dentro do Dota para iniciar sem Alt+Tab.')
        self.worker = threading.Thread(target=self.run, args=(observe,), daemon=True)
        self.worker.start()

    def post(self, text, frame=None):
        try:
            self.messages.put_nowait((text, frame))
        except queue.Full:
            pass

    def run(self, observe):
        held = None
        def move(value):
            nonlocal held
            desired = {-1: 0x41, 1: 0x44}.get(value) if not observe else None
            if desired == held:
                return
            if held is not None:
                USER.keybd_event(held, 0, 2, 0)
            held = None
            if desired is not None and dota_focused() and not self.stop.is_set():
                USER.keybd_event(desired, 0, 0, 0)
                held = desired
        try:
            tracker = Tracker(self.config, self.ball, self.paddle)
            launcher = LaunchPrompt(Path(getattr(sys, '_MEIPASS', Path(__file__).parent))/'launch_ready.png')
            launch_trace = deque(maxlen=120)
            last_launch = None
            last_prompt_scan=None
            paused, was_f8, was_f10, report = False, False, False, 0
            with mss.MSS() as capture:
                while not self.stop.is_set():
                    now = time.perf_counter()
                    if USER.GetAsyncKeyState(0x78) & 0x8000:
                        break
                    f8 = bool(USER.GetAsyncKeyState(0x77) & 0x8000)
                    if f8 and not was_f8:
                        paused = not paused
                        tracker.reset_motion()
                        launcher.reset_observation()
                        last_prompt_scan=None
                    was_f8 = f8
                    if paused or not dota_focused():
                        move(0)
                        tracker.reset_motion()
                        launcher.reset_observation()
                        last_prompt_scan=None
                        if now-report > .3:
                            self.post('Pausado (F8 retoma).' if paused else 'Aguardando você voltar ao Dota 2. Teclas soltas.')
                            report = now
                        self.stop.wait(.025)
                        continue
                    frame = np.asarray(capture.grab(self.config['arena']))[:, :, :3]
                    preview, command, valid, ball, paddle = tracker.step(frame, time.perf_counter())
                    # The launch instruction need not be scanned 20+ times per
                    # second during normal play. Visible prompts still update each frame.
                    launch=False
                    if launcher.visible or last_prompt_scan is None or now-last_prompt_scan>=.15:
                        launch = launcher.update(time.perf_counter(), frame, paddle >= self.config['threshold_paddle'],
                                                 enabled=self.auto_launch_enabled and not observe)
                        last_prompt_scan=now
                    if launcher.visible and self.auto_launch_enabled and not observe:
                        command=0
                    launch_trace.append({'time':time.perf_counter(),'valid':bool(valid),'ball':tracker.ball_box,
                                         'paddle':tracker.paddle_box,'reason':launcher.reason,'request':launch,
                                         'prompt_score':launcher.score,'prompt_visible':launcher.visible,
                                         'ball_score':ball,'paddle_score':paddle,'paddle_method':tracker.paddle_method,
                                         'tracking_reason':tracker.tracking_reason,'command':command,
                                         'target':tracker.last_target,'frame_ms':(time.perf_counter()-now)*1000})
                    if launch:
                        move(0)
                        def launch_allowed():
                            return (not self.stop.is_set() and self.auto_launch_enabled and dota_focused()
                                    and not (USER.GetAsyncKeyState(0x77) & 0x8000)
                                    and not (USER.GetAsyncKeyState(0x78) & 0x8000))
                        sent = double_space(lambda: USER.keybd_event(0x20, 0x39, 0, 0),
                                            lambda: USER.keybd_event(0x20, 0x39, 2, 0),
                                            launch_allowed, self.stop.wait)
                        last_launch = {'time':time.perf_counter(),'sequence_completed':sent}
                        if USER.GetAsyncKeyState(0x77) & 0x8000:
                            paused = True
                            was_f8 = True
                        tracker.reset_motion()
                        command = 0
                        self.post('Instrução de lançamento: Espaço enviado duas vezes.' if sent else 'Relançamento interrompido; teclas soltas.', preview)
                    f10 = bool(USER.GetAsyncKeyState(0x79) & 0x8000)
                    if f10 and not was_f10:
                        folder = DATA / 'diagnosticos' / (time.strftime('%Y%m%d-%H%M%S')+f'-{time.time_ns()%1000000000:09d}')
                        state={'config': self.config, 'ball_score': ball,
                            'paddle_score': paddle, 'valid': valid, 'auto_launch_enabled':self.auto_launch_enabled,
                            'launch_reason':launcher.reason,'prompt_score':launcher.score,'prompt_visible':launcher.visible,
                            'app_version':APP_VERSION,'interface_language':getattr(self, 'language', 'pt-BR'),
                            'prompt_method':launcher.method,
                            'last_launch':last_launch,'paddle_method':tracker.paddle_method,
                            'tracking_reason':tracker.tracking_reason,'command':command,'target':tracker.last_target}
                        self.diagnostic_writer.submit(folder,{'arena':frame,'deteccao':preview,'bola':self.ball,'raquete':self.paddle},
                                                      state,list(launch_trace),self.post)
                    was_f10 = f10
                    move(command)
                    if now-report > .12:
                        state = ('Detectando • raquete recuperada pela faixa vermelha' if tracker.paddle_method=='red-band'
                                 else 'Detectando') if valid else {
                                     'paddle-lost':'Raquete não reconhecida — A/D soltos',
                                     'boot-lost':'Bota não reconhecida — A/D soltos',
                                     'jump-rejected':'Salto de detecção rejeitado — A/D soltos',
                                 }.get(tracker.tracking_reason,'Aguardando detecção — A/D soltos')
                        if launcher.visible:state=launcher.reason
                        self.post(message('{state} • Bola {ball:.0%} • Raquete {paddle:.0%} • {mode}',
                                          state=state, ball=ball, paddle=paddle,
                                          mode='Observação' if observe else 'Controle A/D'), preview)
                        report = now
                    self.stop.wait(max(0, 1/60-(time.perf_counter()-now)))
        except Exception as exc:
            self.post(message('Erro: {error}', error=str(exc)))
        finally:
            move(0)
            self.stop.set()

    def halt(self):
        self.stop.set()
        self.status.set('Parando e soltando as teclas…' if self.worker and self.worker.is_alive() else 'Parado.')

    def hotkeys(self, keys, focused):
        """Edge-triggered starts: holding F7 never repeatedly restarts a run."""
        pressed = keys - self.hotkeys_down
        self.hotkeys_down = keys
        if self.closing or self.stage is not None or self.countdown is not None:
            return
        if 0x78 in keys:
            if self.worker and self.worker.is_alive():
                self.halt()
            return
        if not focused or (self.worker and self.worker.is_alive()):
            return
        if 0x75 in pressed or 0x76 in pressed:
            if not self.config:
                self.status.set('Calibre primeiro na interface. Depois volte ao Dota e aperte F7.')
                return
            self.start(observe=0x76 not in pressed)

    def poll(self):
        try:
            while True:
                text, frame = self.messages.get_nowait()
                self.status.set(text)
                if frame is not None and self.stage is None:
                    self.show(frame)
        except queue.Empty:
            pass
        if self.worker and not self.worker.is_alive():
            self.worker = None
            self.busy(False)
            self.instruction.set('Parado. Dentro do Dota: F6 testa sem teclas; F7 inicia o controle.')
        if not self.testing:
            keys = {key for key in (0x75, 0x76, 0x78) if USER.GetAsyncKeyState(key) & 0x8000}
            self.hotkeys(keys, dota_focused())
        self.root.after(80, self.poll)

    def close(self):
        self.closing = True
        self.stop.set()
        if (self.worker and self.worker.is_alive()) or self.diagnostic_writer.busy():
            self.root.after(50, self.close)
            return
        self.root.destroy()


def main():
    global DATA
    fresh_profile=None
    if '--fresh-profile-test' in sys.argv or '--self-test' in sys.argv:
        import tempfile
        fresh_profile=tempfile.TemporaryDirectory(prefix='dota-calibration-check-')
        DATA=Path(fresh_profile.name)/'profile'
    root = tk.Tk()
    app = App(root)
    # Automated GUI check uses synthetic data and never sends game inputs.
    if '--self-test' in sys.argv:
        output = Path(sys.argv[sys.argv.index('--self-test')+1])
        def check():
            try:
                if fresh_profile is not None:
                    assert app.calibration_source=='embedded'
                    assert app.config['arena']=={'left':817,'top':190,'width':551,'height':725}
                    assert not DATA.exists()  # No local calibration was needed or overwritten.
                rng = np.random.default_rng(7)
                frame = np.zeros((480, 360, 3), dtype=np.uint8)
                frame[:] = (30, 23, 18)
                ball = rng.integers(20, 240, (14, 14, 3), dtype=np.uint8)
                paddle = rng.integers(20, 240, (18, 70, 3), dtype=np.uint8)
                frame[220:234, 160:174] = ball
                frame[420:438, 140:210] = paddle
                config = {'paddle_y': 420, 'paddle_band': 35, 'threshold_ball': .6,
                          'threshold_paddle': .7, 'deadzone': 8}
                tracker = Tracker(config, ball, paddle)
                prompt = LaunchPrompt(Path(getattr(sys, '_MEIPASS', Path(__file__).parent))/'launch_ready.png')
                prompt_frame = np.zeros((725,551,3), np.uint8)
                template = cv2.cvtColor(prompt.template, cv2.COLOR_GRAY2BGR)
                th,tw = template.shape[:2]
                prompt_frame[416:416+th,125:125+tw] = template
                assert sum(prompt.update(2+i*.05,prompt_frame,True) for i in range(40)) == 1
                preview, command, valid, bs, ps = tracker.step(frame, 1.0)
                assert valid and command == 0 and bs > .99 and ps > .99
                moved = frame.copy()
                moved[220:234, 160:174] = (30, 23, 18)
                moved[225:239, 163:177] = ball
                assert tracker.step(moved, 1.02)[2]
                lost = np.zeros_like(frame)
                assert tracker.step(lost, 1.04)[1:3] == (0, False)
                app.show(preview)
                root.update_idletasks()
                # Exercise reverse drag and coordinate mapping without OS input.
                from types import SimpleNamespace
                app.stage = 0
                app.current_frame = frame
                app.drag_start(SimpleNamespace(x=100, y=100))
                app.drag_end(SimpleNamespace(x=20, y=30))
                assert app.selection[2] > 0 and app.selection[3] > 0
                # A language switch must not disturb calibration or the running controller.
                selection, box, config_before, canvas_items = app.selection, app.box_id, app.config, app.canvas.find_all()
                active_worker = SimpleNamespace(is_alive=lambda: True)
                app.worker = active_worker
                app.status.set(message('{state} • Bola {ball:.0%} • Raquete {paddle:.0%} • {mode}',
                                       state='Detectando', ball=.91, paddle=.82, mode='Controle A/D'))
                app.language = 'pt-BR'
                app.toggle_language()
                assert app.language == 'en' and app.calibrate_button.cget('text') == '1. Calibrate'
                assert app.status.get() == 'Tracking • Ball 91% • Paddle 82% • A/D controls'
                assert app.selection == selection and app.box_id == box and app.config is config_before
                assert app.canvas.find_all() == canvas_items and app.worker is active_worker and not app.stop.is_set()
                assert load_language(DATA) == 'en'
                app.toggle_language()
                assert app.language == 'pt-BR' and app.calibrate_button.cget('text') == '1. Calibrar'
                assert app.selection == selection and app.worker is active_worker
                app.worker = None
                app.cancel_calibration()
                app.show(preview)
                # Test start shortcuts without running capture or injecting keys.
                original_start, original_config = app.start, app.config
                calls = []
                app.config = config
                app.start = lambda observe: calls.append(observe)
                app.hotkeys({0x76}, False)
                assert not calls  # Requires Dota focus.
                app.hotkeys(set(), True)
                app.hotkeys({0x76}, True)
                app.hotkeys({0x76}, True)
                assert calls == [False]  # F7 starts once, in control mode.
                app.hotkeys(set(), True)
                app.hotkeys({0x75}, True)
                assert calls == [False, True]  # F6 observes without inputs.
                app.stage = 0
                app.hotkeys(set(), True)
                app.hotkeys({0x76}, True)
                assert calls == [False, True]  # No start during calibration.
                app.stage = None
                app.start, app.config = original_start, original_config
                app.status.set('Teste isolado: interface, prévia, seleção e detecção aprovados.')
                root.update()
                def check_layout(widget):
                    for child in widget.winfo_children():
                        assert child.winfo_x()+child.winfo_width() <= widget.winfo_width(), str(child)
                        assert child.winfo_y()+child.winfo_height() <= widget.winfo_height(), str(child)
                        check_layout(child)
                for language in ('pt-BR', 'en'):
                    app.language = language
                    app.apply_language()
                    for geometry in ('1020x810', '820x700'):
                        root.geometry(geometry)
                        root.update()
                        app.show(preview)
                        root.update()
                        check_layout(root)
                        suffix = '' if geometry == '1020x810' else '-small'
                        snapshot_window(root, output.with_name(f'{output.stem}-{language}{suffix}{output.suffix}'))
                app.language = 'pt-BR'
                app.apply_language()
                root.geometry('1020x810')
                root.update()
                snapshot_window(root, output)
                output.with_suffix('.json').write_text(json.dumps({'passed': True, 'checks': [
                    'window', 'preview', 'reverse_selection', 'template_tracking', 'lost_target_releases', 'first_frame_neutral',
                    'F7_start_once', 'F6_observe', 'hotkeys_require_dota_focus', 'no_start_during_calibration',
                    'bundled_launch_prompt', 'prompt_without_boot_detection', 'live_language_switch_keeps_selection',
                    'live_language_switch_keeps_worker', 'language_saved', 'translated_runtime_status',
                    'PT_EN_layout_at_normal_and_minimum_size'],
                    'fresh_profile_embedded_calibration':fresh_profile is not None}))
            except Exception:
                import traceback
                output.with_suffix('.error.txt').write_text(traceback.format_exc())
            finally:
                app.close()
        root.after(700, check)
    root.mainloop()
    if fresh_profile is not None:fresh_profile.cleanup()


if __name__ == '__main__':
    main()
