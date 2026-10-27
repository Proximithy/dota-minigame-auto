"""Recognize the actual launch instruction, independently of the flying boot."""
from pathlib import Path
import cv2


class LaunchPrompt:
    def __init__(self, template_path, dwell=.8):
        self.template=cv2.imread(str(template_path),cv2.IMREAD_GRAYSCALE)
        if self.template is None:raise ValueError('Referência de relançamento ausente no aplicativo.')
        self.dwell=dwell
        self.latched=False
        self.visible=False
        self.score=0.
        self.reason='aguardando instrução de lançamento'
        self.reset_observation()

    def reset_observation(self):
        self.since=self.last_time=self.absent_since=None
        self.samples=0

    def detect(self,frame):
        normalized=cv2.resize(frame,(551,725))
        gray=cv2.cvtColor(normalized,cv2.COLOR_BGR2GRAY)
        roi=gray[350:510,75:476]
        best=-1.
        for scale in (.95,1.,1.05):
            template=cv2.resize(self.template,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
            result=cv2.matchTemplate(roi,template,cv2.TM_CCOEFF_NORMED)
            best=max(best,float(cv2.minMaxLoc(result)[1]))
        self.score=best
        self.visible=best>=.85
        return self.visible

    def update(self,now,frame,paddle_valid,enabled=True):
        visible=self.detect(frame)
        if not enabled:
            self.reset_observation();self.reason='relançamento desativado/observação';return False
        if self.last_time is not None and (now<=self.last_time or now-self.last_time>.30):
            self.reset_observation()
        self.last_time=now
        if self.latched:
            self.reason='Espaços já enviados; aguardando a instrução desaparecer'
            if not visible:
                if self.absent_since is None:self.absent_since=now
                if now-self.absent_since>=.5:
                    self.latched=False;self.reset_observation()
            else:self.absent_since=None
            return False
        if not visible or not paddle_valid:
            self.since=None;self.samples=0
            self.reason='instrução de lançamento não visível' if not visible else 'aguardando raquete reconhecida'
            return False
        if self.since is None:self.since=now
        self.samples+=1
        self.reason=f'Instrução de lançamento detectada: {now-self.since:.1f}/{self.dwell:.1f}s'
        if now-self.since>=self.dwell and self.samples>=6:
            self.latched=True;self.reason='enviar dois Espaços pela instrução de lançamento';return True
        return False
