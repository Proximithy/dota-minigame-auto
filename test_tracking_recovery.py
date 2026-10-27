import json
from pathlib import Path
import unittest
import cv2
import numpy as np
from tracker import Tracker

ROOT=Path(__file__).parent/'tracking-fixtures/tracking-0009'


class RecoveryTests(unittest.TestCase):
    def load(self,name):
        p=ROOT/name
        c=json.loads((p/'estado.json').read_text())['config']
        ball=cv2.imread(str(p/'bola.png'));paddle=cv2.imread(str(p/'raquete.png'));frame=cv2.imread(str(p/'arena.png'))
        return c,ball,paddle,frame

    def test_real_paddle_animation_fallback_and_absent_boot(self):
        for name,expected_x,method in [('20261027-000907',427,'template'),('20261027-000924',248,'red-band'),('20261027-000925',250,'template')]:
            with self.subTest(name=name):
                c,ball,paddle,frame=self.load(name);tracker=Tracker(c,ball,paddle)
                _,command,valid,bs,ps=tracker.step(frame,1)
                self.assertGreaterEqual(ps,c['threshold_paddle'])
                self.assertEqual(tracker.paddle_method,method)
                x,y,w,h=tracker.paddle_box
                self.assertLess(abs(x+w/2-expected_x),5)
                if name!='20261027-000907':
                    self.assertFalse(valid);self.assertEqual(command,0)  # Boot is actually absent, not invented.

    def test_real_missing_roof_is_not_recovered_from_scenery(self):
        for name,x in [('20261027-000907',374),('20261027-000924',192),('20261027-000925',196)]:
            with self.subTest(name=name):
                c,ball,paddle,frame=self.load(name)
                frame[600:715,x-5:x+115]=(20,10,5)
                tracker=Tracker(c,ball,paddle);result=tracker.step(frame,1)
                self.assertLess(result[4],c['threshold_paddle'])
                self.assertFalse(result[2]);self.assertEqual(result[1],0)

    def test_moving_boot_survives_real_cart_pose_changes(self):
        names=['20261027-000907','20261027-000924','20261027-000925']
        c,ball,paddle,_=self.load(names[0]);tracker=Tracker(c,ball,paddle)
        for i in range(12):
            _,_,_,frame=self.load(names[i%3])
            frame[510:565,410:465]=(20,10,5)  # Remove the source frame's original boot.
            # Keep the inserted trajectory in open arena space, not inside bricks.
            x,y=100+i*3,430+i*5
            h,w=ball.shape[:2];frame[y:y+h,x:x+w]=ball
            result=tracker.step(frame,1+i*.05)
            self.assertTrue(result[2],(i,result[3:],tracker.tracking_reason))
            bx,by,bw,bh=tracker.ball_box
            self.assertLess(abs(bx+bw/2-(x+w/2)),15)
            self.assertLess(abs(by+bh/2-(y+h/2)),15)
            if i>0:self.assertNotEqual(result[1],0)


if __name__=='__main__':unittest.main()
