"""Capture completion signals for a controller polling on another thread."""
import unittest
import numpy as np

from rubik_robot.vision.face_scanner import FaceScanner, new_camera_scanner


class TestFaceSavedSignal(unittest.TestCase):
    def test_material_sampling_switch_does_not_restart_fixed_patch_hold(self):
        scanner = FaceScanner(stable_seconds=.3, min_samples=4, require_transition=True)
        grid = [['blue']*3 for _ in range(3)]
        fixed = np.full((3, 3, 3), (105, 55, 134), dtype=float)
        for index in range(6):
            selected = np.full((3, 3, 3), (109, 104, 119) if index % 2 else (114, 255, 54), dtype=float)
            scanner.update(grid, now=index*.1, hsv_grid=selected, displayed_grid=grid,
                           stability_hsv_grid=fixed)
        self.assertTrue(scanner.consume_face_saved())
        self.assertEqual(scanner.snapshot()['faces']['blue'], ('blue',)*9)

    def test_fixed_patch_change_still_restarts_hold(self):
        scanner = FaceScanner(stable_seconds=.3, min_samples=4, require_transition=True)
        grid = [['white']*3 for _ in range(3)]
        selected = np.full((3, 3, 3), (0, 0, 180), dtype=float)
        for index, brightness in enumerate((200, 200, 200, 150, 150)):
            fixed = np.full((3, 3, 3), (0, 0, brightness), dtype=float)
            scanner.update(grid, now=index*.1, hsv_grid=selected, stability_hsv_grid=fixed)
        self.assertFalse(scanner.consume_face_saved())
        self.assertEqual(scanner.snapshot()['faces'], {})

    def test_camera_captures_at_reduced_hold_and_still_requires_ten_samples(self):
        scanner = new_camera_scanner()
        grid = [['blue']*3 for _ in range(3)]
        for index in range(9):
            self.assertIs(scanner.update(grid, now=index*.15), False)
        self.assertIs(scanner.update(grid, now=1.35), True)
        self.assertTrue(scanner.consume_face_saved())

    def test_shorter_hold_does_not_accept_uncertain_stickers(self):
        scanner = new_camera_scanner()
        grid = [['blue']*3 for _ in range(3)]
        grid[1][2] = ''
        for index in range(20):
            self.assertIs(scanner.update(grid, now=index*.15), False)
        self.assertFalse(scanner.consume_face_saved())
        self.assertEqual(scanner.snapshot()['faces'], {})

    def setUp(self):
        self.scanner = FaceScanner(stable_seconds=.1, min_samples=2)

    def capture(self, color, start=0):
        grid = [[color]*3 for _ in range(3)]
        self.assertIs(self.scanner.update(grid, now=start), False)
        self.assertIs(self.scanner.update(grid, now=start+.2), True)

    def test_signal_survives_later_frames_and_is_consumed_once(self):
        self.capture('red')
        self.assertIs(self.scanner.update([['red']*3 for _ in range(3)], now=1), False)
        self.assertTrue(self.scanner.consume_face_saved())
        self.assertFalse(self.scanner.consume_face_saved())

    def test_each_capture_is_preserved_until_read(self):
        self.capture('red')
        self.capture('blue', 1)
        self.assertTrue(self.scanner.consume_face_saved())
        self.assertTrue(self.scanner.consume_face_saved())
        self.assertFalse(self.scanner.consume_face_saved())

    def test_edit_and_rotation_do_not_signal_a_capture(self):
        self.capture('red')
        self.scanner.consume_face_saved()
        self.scanner.edit('red', 0, 'blue')
        self.scanner.rotate('red')
        self.assertFalse(self.scanner.consume_face_saved())

    def test_forget_and_reset_discard_stale_signals(self):
        self.capture('red')
        self.scanner.forget('red')
        self.assertFalse(self.scanner.consume_face_saved())
        self.capture('red', 1)
        self.scanner.reset()
        self.assertFalse(self.scanner.consume_face_saved())

    def test_manual_capture_signals_only_new_face(self):
        self.scanner.set_enabled(False)
        self.scanner.update([['red']*3 for _ in range(3)], now=0)
        self.assertTrue(self.scanner.save_current())
        self.assertTrue(self.scanner.consume_face_saved())
        self.assertTrue(self.scanner.save_current())
        self.assertFalse(self.scanner.consume_face_saved())
