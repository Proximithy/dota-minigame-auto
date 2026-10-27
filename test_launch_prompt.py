from pathlib import Path
import unittest
import cv2
from launch_prompt import LaunchPrompt

ROOT=Path(__file__).parent


class PromptTests(unittest.TestCase):
    def setUp(self):
        self.frame=cv2.imread(str(ROOT/'tracking-fixtures/launch-wait/arena.png'))
        self.prompt=LaunchPrompt(ROOT/'launch_ready.png')

    def test_real_wait_frame_triggers_without_boot_detection(self):
        self.assertTrue(self.prompt.detect(self.frame))
        self.assertGreater(self.prompt.score,.98)
        events=[self.prompt.update(i*.05,self.frame,True) for i in range(90)]
        self.assertEqual(sum(events),1)

    def test_real_gameplay_and_removed_instruction_are_negative(self):
        for path in (ROOT/'tracking-fixtures/diagnostics').glob('*/arena.png'):
            with self.subTest(frame=path.parent.name):self.assertFalse(self.prompt.detect(cv2.imread(str(path))))
        without=self.frame.copy();without[410:455,115:435]=(20,10,5)
        self.assertFalse(self.prompt.detect(without))

    def test_resize_and_jpeg(self):
        for size in [(441,580),(661,870),(551,725)]:
            image=cv2.resize(self.frame,size)
            image=cv2.imdecode(cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,90])[1],cv2.IMREAD_COLOR)
            self.assertTrue(self.prompt.detect(image), (size,self.prompt.score))

    def test_observation_missing_paddle_and_sparse_frames_do_not_trigger(self):
        for i in range(60):
            self.assertFalse(self.prompt.update(i*.05,self.frame,True,False))
            self.assertFalse(self.prompt.update(i*.05+.001,self.frame,False,True))
        for i in range(10):self.assertFalse(self.prompt.update(4+i*.5,self.frame,True))

    def test_rearms_only_after_instruction_disappears(self):
        self.assertEqual(sum(self.prompt.update(i*.05,self.frame,True) for i in range(40)),1)
        self.prompt.reset_observation()
        self.assertFalse(any(self.prompt.update(3+i*.05,self.frame,True) for i in range(30)))
        play=cv2.imread(str(ROOT/'tracking-fixtures/diagnostics/20261026-212847/arena.png'))
        for i in range(20):self.assertFalse(self.prompt.update(5+i*.05,play,True))
        self.assertEqual(sum(self.prompt.update(7+i*.05,self.frame,True) for i in range(30)),1)


if __name__=='__main__':unittest.main()
