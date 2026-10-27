"""Prefer a newer saved calibration; otherwise use the embedded user default."""
import json
from pathlib import Path
import cv2
import numpy as np
from tracker import Tracker


def read_calibration(folder):
    folder=Path(folder)
    config=json.loads((folder/'config.json').read_text(encoding='utf-8'))
    arena=config['arena']
    if any(type(arena[key]) is not int for key in ('left','top','width','height')) or min(arena['width'],arena['height'])<80:
        raise ValueError('Arena inválida na calibração.')
    ball=cv2.imdecode(np.frombuffer((folder/'ball.png').read_bytes(),np.uint8),cv2.IMREAD_COLOR)
    paddle=cv2.imdecode(np.frombuffer((folder/'paddle.png').read_bytes(),np.uint8),cv2.IMREAD_COLOR)
    if ball is None or paddle is None:raise ValueError('Recortes inválidos na calibração.')
    Tracker(config,ball,paddle)
    return config,ball,paddle


def load_calibration(saved,embedded):
    for source,folder in [('saved',saved),('embedded',embedded)]:
        try:return (*read_calibration(folder),source)
        except (OSError,ValueError,KeyError,TypeError,AttributeError,cv2.error):continue
    return None
