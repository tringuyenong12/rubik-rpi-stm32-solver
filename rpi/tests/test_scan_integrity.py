"""A displayed blue sticker must not silently become white in saved/solver data."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import cv2

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.vision.face_scanner import FaceScanner, new_camera_scanner
from rubik_robot.vision.scan_audit import write_audit
from rubik_robot.vision.scan_preview import StableScanPreview
from rubik_robot.vision.solve_guide import apply_move, cube_faces, prepare_cube, rotate_grid, verify_scan_colors
from twophase import vision2, vision_params


class TestScanIntegrity(unittest.TestCase):
    def test_low_fps_camera_saves_the_same_colors_it_displays(self):
        scanner, preview = new_camera_scanner(), StableScanPreview()
        frame = np.full((120, 120, 3), 80, dtype=np.uint8)
        colors = [['blue']*3 for _ in range(3)]
        boxes = [np.float32([[x, y], [x+20, y], [x+20, y+20], [x, y+20]])
                 for y in (10, 45, 80) for x in (10, 45, 80)]
        for index in range(16):
            shown, _ = preview.update(frame, colors, boxes, (0, 0, 120, 120), now=index*.5)
            scanner.update(colors, now=index*.5, displayed_grid=shown)
        self.assertEqual(scanner.snapshot()['faces']['blue'], ('blue',)*9)
        self.assertEqual(shown, colors)

    def test_preview_and_current_colors_must_agree_before_auto_or_manual_capture(self):
        scanner = FaceScanner(stable_seconds=.1, min_samples=2)
        blue = [['blue']*3 for _ in range(3)]
        white = [['white']*3 for _ in range(3)]
        for now in (0, .1, .2, .3):
            scanner.update(blue, now=now, displayed_grid=white)
        self.assertFalse(scanner.snapshot()['faces'])
        self.assertFalse(scanner.save_current())
        scanner.update(blue, now=.4, displayed_grid=blue)
        self.assertEqual(scanner.snapshot()['faces']['blue'], ('blue',)*9)

    def test_one_sticker_changed_late_needs_a_fresh_full_hold(self):
        scanner = new_camera_scanner()
        blue = [['blue']*3 for _ in range(3)]
        for index in range(28):
            scanner.update(blue, now=.8*scanner.stable_seconds*index/28)
        changed = [['blue']*3 for _ in range(3)]
        changed[0][2] = 'white'
        change_start = scanner.stable_seconds * .85
        for index in range(29):
            scanner.update(changed, now=change_start+scanner.stable_seconds*index/29)
        self.assertFalse(scanner.snapshot()['faces'])
        scanner.update(changed, now=change_start+.1+scanner.stable_seconds)
        self.assertEqual(scanner.snapshot()['faces']['blue'][2], 'white')

    def test_default_solver_preparation_cannot_recolor_a_blue_white_error(self):
        faces = {center: list(values) for center, values in cube_faces(SOLVED_CUBE).items()}
        faces['blue'][0] = 'white'
        prototypes = {'yellow': (30, 230, 220), 'green': (60, 220, 190), 'red': (1, 230, 210),
                      'white': (0, 10, 220), 'blue': (115, 230, 200), 'orange': (17, 230, 230)}
        samples = {center: (prototypes[center],)*9 for center in faces}
        with self.assertRaises(ValueError):
            prepare_cube(faces, samples)
        self.assertEqual(faces['blue'][0], 'white')

    def test_correspondence_accepts_face_rotations_but_rejects_different_color_layouts(self):
        original = apply_move(SOLVED_CUBE, 'R')
        faces = {center: rotate_grid(values, 1) for center, values in cube_faces(original).items()}
        verify_scan_colors(faces, original)
        with self.assertRaisesRegex(ValueError, 'changes captured sticker colors'):
            verify_scan_colors(faces, apply_move(SOLVED_CUBE, 'U'))

    def test_washed_out_blue_or_mixed_glare_is_not_accepted_as_white(self):
        with patch.object(vision_params, 'sat_W', 35):
            for hue, saturation, expected in ((110, 20, ''), (110, 85, 'blue'), (70, 8, 'white')):
                hsv = np.full((40, 40, 3), (hue, saturation, 200), dtype=np.float32)
                with patch.multiple(vision2, hsv=hsv, width=40, height=40, create=True):
                    self.assertEqual(vision2.getcolor((20, 20), 18)[1], expected)
            hsv = np.full((40, 40, 3), (70, 8, 220), dtype=np.float32)
            hsv[:, :15] = (110, 120, 180)
            with patch.multiple(vision2, hsv=hsv, width=40, height=40, create=True):
                self.assertEqual(vision2.getcolor((20, 20), 18)[1], '')
            hsv = np.full((80, 80, 3), (110, 120, 180), dtype=np.float32)
            hsv[22:58, 22:58] = (0, 0, 255)
            with patch.multiple(vision2, hsv=hsv, width=80, height=80, create=True):
                self.assertEqual(vision2.getcolor((40, 40), 18)[1], 'blue')
            hsv = np.full((40, 40, 3), (15, 8, 80), dtype=np.float32)
            with patch.multiple(vision2, hsv=hsv, width=40, height=40, create=True):
                self.assertEqual(vision2.getcolor((20, 20), 18)[1], '')

    def test_audit_preserves_actual_saved_colors(self):
        with TemporaryDirectory() as directory:
            payload = {'faces': {'blue': ['blue']*9}, 'status': 'captured'}
            write_audit('scan', payload, directory)
            saved = json.loads((Path(directory)/'scan.json').read_text(encoding='utf-8'))
            self.assertEqual(saved, payload)
            self.assertFalse((Path(directory)/'scan.json.tmp').exists())

    def test_specular_blue_patch_stays_blue_in_the_saved_cube_face(self):
        frame = np.full((480, 640, 3), 20, dtype=np.uint8)
        palette = [(220,70,0), (220,70,0), (230,230,230), (0,180,0), (220,70,0),
                   (220,70,0), (0,180,0), (230,230,230), (0,230,255)]
        for index, color in enumerate(palette):
            x, y = 150+index%3*120, 70+index//3*120
            cv2.rectangle(frame, (x, y), (x+96, y+96), color, -1)
        cv2.circle(frame, (438, 238), 22, (255, 255, 255), -1)
        roi = ((138, 58), (497, 58), (497, 417), (138, 417))
        scanner, preview = new_camera_scanner(), StableScanPreview()
        for index in range(56):
            samples, colors = vision2.detect_face(frame, roi, include_masks=False)
            displayed, _ = preview.update(frame, colors, vision2.face_boxes, roi, now=index/30)
            scanner.update(colors, now=index/30, hsv_grid=samples, displayed_grid=displayed)
        saved = scanner.snapshot()['faces']['blue']
        self.assertEqual(saved, ('blue', 'blue', 'white', 'green', 'blue', 'blue', 'green', 'white', 'yellow'))
        self.assertEqual(saved[5], 'blue')


if __name__ == '__main__':
    unittest.main()
