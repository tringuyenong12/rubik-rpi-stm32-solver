"""Prevent center flicker and unfinished turns from creating saved faces."""
import unittest

import numpy as np

from rubik_robot.vision.face_scanner import FaceScanner, new_camera_scanner
from twophase import vision2


class TestScanTransition(unittest.TestCase):
    def setUp(self):
        self.scanner = FaceScanner(stable_seconds=.75, min_samples=8, require_transition=True)
        self.white = [['white'] * 3 for _ in range(3)]

    def hold(self, grid, start=0, hsv=None):
        for index in range(17):
            self.scanner.update(grid, now=start+index*.05, hsv_grid=hsv)

    def test_saved_face_cannot_be_relabelled_by_center_flicker(self):
        self.hold(self.white)
        changed = [['white'] * 3, ['white', 'red', 'white'], ['white'] * 3]
        self.hold(changed, 1)
        self.hold(changed, 3)
        self.assertEqual(set(self.scanner.snapshot()['faces']), {'white'})
        self.assertIn('Center uncertain', self.scanner.snapshot()['message'])

    def test_short_turn_does_not_save_but_a_held_new_face_does(self):
        self.hold(self.white)
        blue = [['blue'] * 3 for _ in range(3)]
        for index in range(8):
            self.scanner.update(blue, now=1+index*.02)
        self.assertEqual(set(self.scanner.snapshot()['faces']), {'white'})
        self.hold(blue, 1.2)
        self.assertEqual(set(self.scanner.snapshot()['faces']), {'white', 'blue'})

    def test_initial_center_flicker_restarts_full_hold(self):
        for index in range(12):
            self.scanner.update(self.white, now=index*.05)
        red = [['white'] * 3, ['white', 'red', 'white'], ['white'] * 3]
        self.scanner.update(red, now=.6)
        self.scanner.update(self.white, now=.65)
        for index in range(8):
            self.scanner.update(self.white, now=.7+index*.02)
        self.assertFalse(self.scanner.snapshot()['faces'])
        self.hold(self.white, 1)
        self.assertEqual(set(self.scanner.snapshot()['faces']), {'white'})

    def test_changing_stickers_restart_hold_even_with_same_center(self):
        for index in range(12):
            self.scanner.update(self.white, now=index*.05)
        changed = [['red', 'blue', 'white'], ['white'] * 3, ['white'] * 3]
        for index in range(8):
            self.scanner.update(changed, now=.6+index*.03)
        self.assertFalse(self.scanner.snapshot()['faces'])
        self.hold(changed, 1)
        self.assertIn('white', self.scanner.snapshot()['faces'])

    def test_numeric_center_change_restarts_hold_without_a_label_change(self):
        hsv = np.full((3, 3, 3), (0, 0, 200), dtype=float)
        for index in range(12):
            self.scanner.update(self.white, now=index*.05, hsv_grid=hsv)
        shadowed = hsv.copy()
        shadowed[1, 1, 2] = 150
        for index in range(8):
            self.scanner.update(self.white, now=.6+index*.03, hsv_grid=shadowed)
        self.assertFalse(self.scanner.snapshot()['faces'])
        self.hold(self.white, 1, shadowed)
        self.assertIn('white', self.scanner.snapshot()['faces'])

    def test_explicit_rescan_rearms_current_face(self):
        self.hold(self.white)
        self.scanner.forget('white')
        self.hold(self.white, 1)
        self.assertIn('white', self.scanner.snapshot()['faces'])
        self.scanner.reset()
        self.hold(self.white, 2)
        self.assertIn('white', self.scanner.snapshot()['faces'])

    def test_center_near_red_orange_boundary_is_rejected(self):
        from twophase import vision_params
        self.assertFalse(vision2.center_color_confident((vision_params.orange_L+.2, 180, 200), 'orange'))
        self.assertTrue(vision2.center_color_confident((0, 180, 200), 'red'))

    def test_camera_requires_one_and_a_half_seconds_despite_many_fast_frames(self):
        scanner = new_camera_scanner()
        orange = [['orange'] * 3 for _ in range(3)]
        for index in range(30):
            scanner.update(orange, now=index*.05)
        self.assertFalse(scanner.snapshot()['faces'])
        scanner.update(orange, now=1.5)
        self.assertEqual(set(scanner.snapshot()['faces']), {'orange'})

    def test_red_to_orange_correction_gets_a_fresh_long_hold(self):
        scanner = new_camera_scanner()
        for index in range(16):
            scanner.update([['red'] * 3 for _ in range(3)], now=index*.05)
        for index in range(30):
            scanner.update([['orange'] * 3 for _ in range(3)], now=.8+index*.05)
        self.assertFalse(scanner.snapshot()['faces'])
        scanner.update([['orange'] * 3 for _ in range(3)], now=2.31)
        self.assertEqual(set(scanner.snapshot()['faces']), {'orange'})


if __name__ == '__main__':
    unittest.main()
