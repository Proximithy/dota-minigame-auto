"""Controlled moving scenes using the user's actual boot/cart crops, no game input."""
from pathlib import Path
import time
import unittest
import json
import cv2
import numpy as np
from tracker import Tracker

ROOT = Path(__file__).parent


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.ball = cv2.imread(str(ROOT/'tracking-fixtures/ball.png'))
        self.paddle = cv2.imread(str(ROOT/'tracking-fixtures/paddle.png'))
        self.config = {'paddle_y': 590, 'paddle_band': 186, 'deadzone': 20,
                       'threshold_ball': .6, 'threshold_paddle': .7}
        self.tracker = Tracker(self.config, self.ball, self.paddle)
        self.background = np.zeros((721, 549, 3), np.uint8)
        self.background[:] = (35, 15, 8)

    def scene(self, angle=0, position=(180, 180), animate_cart=False, show_ball=True, decoy=False):
        frame = self.background.copy()
        ph, pw = self.paddle.shape[:2]
        frame[590:590+ph, 240:240+pw] = self.paddle
        if animate_cart:
            # Roof stays the same; moving/animated body changes substantially.
            frame[625:590+ph, 240:240+pw] = (20, 35, 45)
        def stamp(angle, center):
            size = 70
            image = np.zeros((size, size, 3), np.uint8)
            image[:] = (35, 15, 8)
            h, w = self.ball.shape[:2]
            image[10:10+h, 10:10+w] = self.ball
            rot = cv2.getRotationMatrix2D((size/2, size/2), angle, 1)
            image = cv2.warpAffine(image, rot, (size, size), borderValue=(35, 15, 8))
            x, y = center[0]-size//2, center[1]-size//2
            frame[y:y+size, x:x+size] = image
        if show_ball:
            stamp(angle, position)
        if decoy:
            stamp(0, (470, 80))
        return frame

    def test_rotating_boot_and_animated_cart(self):
        elapsed = []
        for i, angle in enumerate(range(0, 360, 30)):
            position = (180+i*7, 180+i*8)
            before = time.perf_counter()
            _, _, valid, bs, ps = self.tracker.step(self.scene(angle, position, i > 0, decoy=i > 0), 1+i*.04)
            elapsed.append(time.perf_counter()-before)
            self.assertTrue(valid, (angle, bs, ps))
            x, y, w, h = self.tracker.ball_box
            self.assertLess(abs(x+w/2-position[0]), 22)
            self.assertLess(abs(y+h/2-position[1]), 22)
        print('Tracking milliseconds (first / median):', round(elapsed[0]*1000), round(np.median(elapsed[1:])*1000))

    def test_missing_ball_neutral_and_reacquisition(self):
        self.tracker.step(self.scene(), 1)
        for i in range(1, 12):
            _, command, valid, _, _ = self.tracker.step(self.scene(show_ball=False), 1+i*.04)
            self.assertFalse(valid)
            self.assertEqual(command, 0)
        _, command, valid, _, _ = self.tracker.step(self.scene(90, (380, 350)), 1.5)
        self.assertTrue(valid)
        self.assertEqual(command, 0)  # Reacquisition never uses a stale velocity.

    def test_focus_reset_clears_history(self):
        self.tracker.step(self.scene(), 1)
        self.tracker.reset_motion()
        self.assertIsNone(self.tracker.last_frame)
        self.assertIsNone(self.tracker.previous)
        self.assertIsNone(self.tracker.last_ball)

    def test_prediction_outside_arena_does_not_crash(self):
        self.tracker.step(self.scene(), 1)
        self.tracker.velocity = (-4000, -4000)
        result = self.tracker.step(self.scene(position=(40, 50)), 1.15)
        self.assertEqual(len(result), 5)

    def test_real_f10_frames_and_control_directions(self):
        cases = [('20261026-212839', (471, 660), 1),
                 ('20261026-212845', (430, 547), 1),
                 ('20261026-212846', (355, 431), -1),
                 ('20261026-212847', (294, 638), -1)]
        for name, expected, expected_direction in cases:
            with self.subTest(name=name):
                path = ROOT/'tracking-fixtures/diagnostics'/name
                config = json.loads((path/'estado.json').read_text())['config']
                ball = cv2.imread(str(path/'bola.png'))
                paddle = cv2.imread(str(path/'raquete.png'))
                frame = cv2.imread(str(path/'arena.png'))
                tracker = Tracker(config, ball, paddle)
                _, command, valid, _, _ = tracker.step(frame, 1)
                self.assertTrue(valid)
                self.assertEqual(command, 0)
                x, y, w, h = tracker.ball_box
                self.assertLess(abs(x+w/2-expected[0]), 8)
                self.assertLess(abs(y+h/2-expected[1]), 8)
                self.assertEqual(tracker.step(frame, 1.04)[1], expected_direction)
                # Retain all real decoration but remove just the boot.
                negative = frame.copy()
                negative[max(0,int(y)-4):int(y+h)+4, max(0,int(x)-4):int(x+w)+4] = (20, 10, 4)
                clean = Tracker(config, ball, paddle)
                result = clean.step(negative, 1)
                self.assertFalse(result[2])
                self.assertEqual(result[1], 0)


if __name__ == '__main__':
    unittest.main()
