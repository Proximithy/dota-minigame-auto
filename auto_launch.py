"""One double-Space per stationary launch position; no OS dependencies."""
import math
import time


class AutoLaunch:
    def __init__(self, dwell=2.0):
        self.dwell = dwell
        self.latched = False
        self.fired_at = None
        self.rearm_since = None
        self.reason = 'aguardando detecção'
        self.reset_observation()

    def reset_observation(self):
        # Losing focus or detection cannot rearm an already sent launch.
        self.anchor = None
        self.since = self.last_time = None
        self.samples = 0
        self.rearm_since = None

    def update(self, now, valid, ball_box, paddle_box, enabled=True):
        if not enabled or not valid or ball_box is None or paddle_box is None:
            self.reset_observation()
            self.reason = 'desativado/observação' if not enabled else 'bota ou raquete sem detecção válida'
            return False
        x,y,w,h = ball_box
        px,py,pw,ph = paddle_box
        bx,by = x+w/2,y+h/2
        relative=(bx-(px+pw/2),by-(py+ph/2))
        if self.last_time is not None and (now <= self.last_time or now-self.last_time > .30):
            self.reset_observation()
        self.last_time = now
        if self.latched:
            self.reason = 'Espaço já solicitado; aguardando movimento para rearmar'
            if math.dist(relative,self.fired_at) > max(18,w*.6,h*.6):
                if self.rearm_since is None:self.rearm_since=now
                if now-self.rearm_since >= .20:
                    self.latched=False
                    self.reset_observation()
            else:self.rearm_since=None
            return False
        # A launch-ready boot sits near the cart. A stationary object elsewhere,
        # or a single turning point at a wall, must not cause Space presses.
        nearby = abs(bx-(px+pw/2)) <= max(pw*.85,w) and py-max(h*3,60) <= by <= py+ph+max(h,20)
        if not nearby:
            self.reset_observation()
            self.reason = 'bota fora da região de lançamento'
            return False
        if self.anchor is None or math.dist(relative,self.anchor) > max(7,w*.20,h*.20):
            self.anchor=relative;self.since=now;self.samples=1
            self.reason = 'iniciando confirmação de parada'
            return False
        self.samples+=1
        self.reason = f'parada confirmando {now-self.since:.2f}/{self.dwell:.2f}s ({self.samples} quadros)'
        if now-self.since >= self.dwell and self.samples >= 12:
            self.latched=True;self.fired_at=relative;self.rearm_since=None
            self.reason = 'enviar dois Espaços'
            return True
        return False


def double_space(key_down, key_up, allowed, wait, clock=time.monotonic):
    """Interruptible pulses; always release Space, even on focus loss/errors."""
    def delay(seconds):
        deadline=clock()+seconds
        while clock()<deadline:
            if not allowed():return False
            wait(min(.01,max(0,deadline-clock())))
        return allowed()
    for index in range(2):
        if not allowed():return False
        key_down()
        try:
            if not delay(.08):return False
        finally:
            key_up()
        if index==0 and not delay(.35):return False
    return True
