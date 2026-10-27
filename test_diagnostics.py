import json
from pathlib import Path
import queue
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import cv2
import numpy as np
from diagnostics import DiagnosticWriter
import gui


class DiagnosticTests(unittest.TestCase):
    def test_saved_snapshot_does_not_follow_later_mutations(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer=DiagnosticWriter();image=np.full((20,20,3),50,np.uint8)
            state={'version':'test','command':1};trace=[{'command':1}];messages=[]
            destination=Path(tmp)/'case'
            self.assertTrue(writer.submit(destination,{'arena':image},state,trace,messages.append))
            image[:]=0;state['command']=0;trace[0]['command']=0
            writer.thread.join(5)
            self.assertFalse(writer.busy())
            self.assertEqual(int(cv2.imread(str(destination/'arena.png'))[0,0,0]),50)
            self.assertEqual(json.loads((destination/'estado.json').read_text())['command'],1)
            self.assertEqual(json.loads((destination/'relancamento.json').read_text())[0]['command'],1)

    def test_f10_does_not_release_control_or_reset_tracking(self):
        events=[];saved=[];messages=[];counter=[0];resets=[]
        app=SimpleNamespace(stop=threading.Event(),config={'arena':{},'threshold_paddle':.7},
                            ball=np.zeros((4,4,3),np.uint8),paddle=np.zeros((4,4,3),np.uint8),
                            auto_launch_enabled=True,post=lambda *v:messages.append(v))
        class FakeTracker:
            ball_box=(30,30,10,10);paddle_box=(10,80,30,10)
            paddle_method='template';tracking_reason='tracking';last_target=100
            def __init__(self,*args):pass
            def reset_motion(self):resets.append(1)
            def step(self,frame,now):return frame,1,True,.95,.95
        class FakePrompt:
            visible=False;score=.1;reason='not visible';method='test'
            def __init__(self,*args):pass
            def update(self,*args,**kwargs):return False
            def reset_observation(self):pass
        class FakeScreen:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def grab(self,area):
                counter[0]+=1
                if counter[0]==6:app.stop.set()
                return np.zeros((100,100,4),np.uint8)
        app.diagnostic_writer=SimpleNamespace(submit=lambda *args:saved.append(args) or True)
        user=SimpleNamespace(GetAsyncKeyState=lambda key:0x8000 if key==0x79 and counter[0]==3 else 0,
                             keybd_event=lambda key,scan,flags,extra:events.append((key,flags)))
        with patch.object(gui,'Tracker',FakeTracker),patch.object(gui,'LaunchPrompt',FakePrompt),patch.object(gui.mss,'MSS',FakeScreen),patch.object(gui,'USER',user),patch.object(gui,'dota_focused',return_value=True):
            gui.App.run(app,False)
        self.assertEqual(events,[(0x44,0),(0x44,2)])  # One continuous D hold, then final release.
        self.assertEqual(resets,[])
        self.assertEqual(len(saved),1)
        self.assertFalse(any(str(item[0]).startswith('Erro:') for item in messages),messages)

    def test_only_actual_game_title_passes_focus_guard(self):
        self.assertTrue(gui.is_dota_title('Dota 2'))
        self.assertFalse(gui.is_dota_title('Assistente do Minigame • Dota 2 • v1.0.2'))
        self.assertFalse(gui.is_dota_title('Dota 2 — Microsoft Edge'))


if __name__=='__main__':unittest.main()
