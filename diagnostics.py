"""Save an immutable F10 snapshot off the control thread."""
from copy import deepcopy
import json
from pathlib import Path
import threading
import cv2
from i18n import message


class DiagnosticWriter:
    def __init__(self):self.thread=None

    def busy(self):return self.thread is not None and self.thread.is_alive()

    def submit(self,folder,images,state,trace,callback):
        if self.busy():return False
        images={name:image.copy() for name,image in images.items()}
        state,trace=deepcopy(state),deepcopy(trace)
        def save():
            try:
                folder_path=Path(folder);folder_path.mkdir(parents=True,exist_ok=False)
                for name,image in images.items():
                    okay,encoded=cv2.imencode('.png',image)
                    if not okay:raise ValueError(f'Não foi possível salvar {name}.')
                    (folder_path/f'{name}.png').write_bytes(encoded.tobytes())
                (folder_path/'estado.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
                (folder_path/'relancamento.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
                callback(message('Diagnóstico salvo em {folder}', folder=str(folder_path)))
            except Exception as exc:callback(message('Erro ao salvar diagnóstico: {error}', error=str(exc)))
        self.thread=threading.Thread(target=save,daemon=True);self.thread.start()
        return True
