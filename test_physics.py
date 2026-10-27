import unittest
from physics import direction, intercept, reflect


class PredictionTests(unittest.TestCase):
    def test_wall_bounces(self):
        for raw, expected in [(30, 30), (120, 80), (-20, 20), (320, 80), (-220, 20)]:
            self.assertAlmostEqual(reflect(raw, 0, 100), expected)

    def test_offset_and_ball_radius(self):
        self.assertEqual(reflect(110, 10, 90), 70)

    def test_downward_intercept_with_bounce(self):
        self.assertEqual(intercept(70, 30, 60, 100, 130, 0, 100), 70)

    def test_upward_tracks_current_position(self):
        self.assertEqual(intercept(40, 30, 60, -100, 130, 0, 100), 40)

    def test_keys_and_deadzone(self):
        self.assertEqual(direction(52, 50, 5), 0)
        self.assertEqual(direction(60, 50, 5), 1)
        self.assertEqual(direction(40, 50, 5), -1)


if __name__ == '__main__':
    unittest.main()
