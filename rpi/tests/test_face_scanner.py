"""Verify camera acquisition, deduplication and desktop preview without hardware."""

import unittest
import warnings
from unittest.mock import Mock, patch

import cv2
import numpy as np

from rubik_robot.vision.face_scanner import COLORS, FaceScanner
from twophase import vision2


class TestFaceScanner(unittest.TestCase):
    def capture(self, scanner, color, start=0):
        """Input: session, color and clock. Output: five stable synthetic frames."""
        grid = [[color] * 3 for _ in range(3)]
        for elapsed in (0, .2, .4, .6, .8):
            scanner.update(grid, now=start + elapsed)

    def test_hold_requires_both_time_and_frames(self):
        """Input: fast frames. Output: capture only after the hold time passes."""
        scanner = FaceScanner()
        grid = [['white'] * 3 for _ in range(3)]
        for frame in range(8):
            scanner.update(grid, now=frame * .01)
        self.assertFalse(scanner.snapshot()['faces'])
        scanner.update(grid, now=.8)
        self.assertEqual(scanner.snapshot()['faces']['white'], ('white',) * 9)

    def test_accepts_all_faces_in_any_order(self):
        """Input: shuffled centers. Output: six distinct saved faces."""
        scanner = FaceScanner()
        for index, color in enumerate(reversed(COLORS)):
            self.capture(scanner, color, start=index * 2)
        self.assertEqual(set(scanner.snapshot()['faces']), set(COLORS))

    def test_duplicate_center_keeps_saved_grid(self):
        """Input: a different grid with a saved center. Output: original grid kept."""
        scanner = FaceScanner()
        self.capture(scanner, 'white')
        changed = [['red', 'white', 'white'], ['white'] * 3, ['white'] * 3]
        for now in (2, 3, 4, 5, 6):
            scanner.update(changed, now)
        self.assertEqual(scanner.snapshot()['faces']['white'], ('white',) * 9)

    def test_invalid_frame_breaks_hold(self):
        """Input: interrupted detection. Output: restart frame/time stability."""
        scanner = FaceScanner()
        grid = [['white'] * 3 for _ in range(3)]
        scanner.update(grid, 0)
        scanner.update([], 1)
        scanner.update(grid, 2)
        self.assertFalse(scanner.snapshot()['faces'])
        self.assertEqual(scanner.samples, 1)

    def test_changed_color_breaks_hold(self):
        """Input: flickering sticker color. Output: restart stability for the new grid."""
        scanner = FaceScanner()
        self.capture(scanner, 'white')
        scanner.reset()
        scanner.update([['white'] * 3 for _ in range(3)], 0)
        scanner.update([['red'] * 3 for _ in range(3)], 1)
        self.assertEqual(scanner.samples, 1)
        self.assertFalse(scanner.snapshot()['faces'])

    def test_color_count_does_not_block_the_sixth_face(self):
        """Input: one misclassified sticker. Output: capture all six faces and report counts."""
        scanner = FaceScanner()
        self.capture(scanner, 'white')
        grid = [['red'] * 3 for _ in range(3)]
        grid[0][0] = 'white'
        for now in (2, 2.2, 2.4, 2.6, 2.8):
            scanner.update(grid, now)
        for index, color in enumerate(('green', 'blue', 'yellow', 'orange')):
            self.capture(scanner, color, 4+index*2)
        self.assertEqual(len(scanner.snapshot()['faces']), 6)
        self.assertIn('white=10', scanner.snapshot()['message'])

    def test_rescan_and_reset(self):
        """Input: forget/reset actions. Output: reacquire face and clear session."""
        scanner = FaceScanner()
        self.capture(scanner, 'white')
        scanner.forget('white')
        self.assertFalse(scanner.snapshot()['faces'])
        self.capture(scanner, 'white', 2)
        scanner.reset()
        self.assertFalse(scanner.snapshot()['faces'])
        self.assertFalse(scanner.snapshot()['current'])

    def test_paused_scan_allows_explicit_import(self):
        """Input: paused frames and manual import. Output: only explicit capture saves."""
        scanner = FaceScanner()
        scanner.set_enabled(False)
        self.capture(scanner, 'white')
        self.assertFalse(scanner.snapshot()['faces'])
        self.assertTrue(scanner.save_current())
        self.assertIn('white', scanner.snapshot()['faces'])

    def test_rotation_and_snapshot_are_isolated(self):
        """Input: rotation and edited snapshot. Output: correct rotation and isolated copy."""
        scanner = FaceScanner()
        face = ('red', 'green', 'blue', 'orange', 'white', 'yellow', 'blue', 'red', 'green')
        scanner.update([face[:3], face[3:6], face[6:]], 0)
        self.assertTrue(scanner.save_current())
        scanner.rotate('white')
        self.assertEqual(scanner.snapshot()['faces']['white'],
                         ('blue', 'orange', 'red', 'red', 'white', 'green', 'green', 'yellow', 'blue'))
        state = scanner.snapshot()
        state['faces'].clear()
        self.assertIn('white', scanner.snapshot()['faces'])

    def test_voting_tolerates_one_noisy_sticker(self):
        """Input: one flickering sticker. Output: save the majority color after five frames."""
        scanner = FaceScanner()
        for index, now in enumerate((0, .06, .12, .18, .24)):
            grid = [['white'] * 3 for _ in range(3)]
            if index == 2:
                grid[0][0] = 'red'
            scanner.update(grid, now)
        self.assertEqual(scanner.snapshot()['faces']['white'], ('white',) * 9)

    def test_brief_detection_gap_keeps_votes(self):
        """Input: one missed detection. Output: retain recent votes and capture promptly."""
        scanner = FaceScanner()
        grid = [['white'] * 3 for _ in range(3)]
        scanner.update(grid, 0)
        scanner.update(grid, .07)
        scanner.update([], .10)
        scanner.update(grid, .14)
        scanner.update(grid, .21)
        self.assertIn('white', scanner.snapshot()['faces'])


class TestCameraPreview(unittest.TestCase):
    def synthetic_face(self, size, angle):
        """Input: sticker size/rotation. Output: a mixed-color camera frame and expected grid."""
        frame = np.full((480, 640, 3), 20, dtype=np.uint8)
        palette = ((0, 0, 220), (0, 170, 0), (220, 70, 0), (0, 140, 255),
                   (240, 240, 240), (0, 230, 255), (220, 70, 0), (0, 0, 220), (0, 170, 0))
        spacing = round(size * 1.25)
        for index, color in enumerate(palette):
            x = round(320 - spacing * 1.5 + index % 3 * spacing)
            y = round(240 - spacing * 1.5 + index // 3 * spacing)
            cv2.rectangle(frame, (x, y), (x + size, y + size), color, -1)
        matrix = cv2.getRotationMatrix2D((320, 240), angle, 1)
        frame = cv2.warpAffine(frame, matrix, (640, 480), borderValue=(20, 20, 20))
        expected = [['red', 'green', 'blue'], ['orange', 'white', 'yellow'], ['blue', 'red', 'green']]
        return frame, expected

    def test_small_and_rotated_stickers_form_a_complete_grid(self):
        """Input: small/large rotated faces. Output: nine correctly ordered colors."""
        for size in (18, 30, 50, 80):
            for angle in (0, 15, -20, 30):
                with self.subTest(size=size, angle=angle):
                    frame, expected = self.synthetic_face(size, angle)
                    _, colors = vision2.detect_face(frame)
                    self.assertEqual(colors, expected)

    def test_dark_white_stickers_and_touching_regions(self):
        """Input: shadowed white face with two connected stickers. Output: all nine whites."""
        frame = np.full((480, 640, 3), 20, dtype=np.uint8)
        for row in range(3):
            for col in range(3):
                x, y = 200 + col * 65, 140 + row * 65
                value = 135 if col == 0 else 210
                cv2.rectangle(frame, (x, y), (x + 50, y + 50), (value,) * 3, -1)
        cv2.rectangle(frame, (287, 250), (293, 280), (210, 210, 210), -1)
        _, colors = vision2.detect_face(frame)
        self.assertEqual(colors, [['white'] * 3 for _ in range(3)])

    def test_perspective_face_preserves_sticker_order(self):
        """Input: a tilted camera view. Output: the same row-major color grid."""
        frame, expected = self.synthetic_face(50, 0)
        source = np.float32([[220, 140], [400, 140], [400, 320], [220, 320]])
        target = np.float32([[240, 120], [415, 160], [375, 340], [205, 300]])
        transform = cv2.getPerspectiveTransform(source, target)
        tilted = cv2.warpPerspective(frame, transform, (640, 480), borderValue=(20, 20, 20))
        self.assertEqual(vision2.detect_face(tilted)[1], expected)

    def test_missing_sticker_does_not_create_a_complete_face(self):
        """Input: eight visible stickers. Output: no invented ninth color."""
        frame, _ = self.synthetic_face(40, 0)
        frame[165:211, 245:291] = 20
        _, colors = vision2.detect_face(frame)
        self.assertEqual(colors, [])



    def test_camera_entry_point_detects_and_saves_a_synthetic_face(self):
        """Input: generated camera frames. Output: correct saved face and released camera."""
        frame = np.full((480, 640, 3), 20, dtype=np.uint8)
        palette = ((0, 0, 220), (0, 170, 0), (220, 70, 0), (0, 140, 255),
                   (240, 240, 240), (0, 230, 255), (220, 70, 0), (0, 0, 220), (0, 170, 0))
        for index, color in enumerate(palette):
            x, y = 200 + index % 3 * 65, 150 + index // 3 * 65
            cv2.rectangle(frame, (x, y), (x + 50, y + 50), color, -1)
        camera = Mock()
        camera.isOpened.return_value = True
        camera.read.side_effect = [(True, frame.copy()) for _ in range(3)] + [(False, None)]
        session = FaceScanner(stable_seconds=0, min_samples=2)
        with patch.object(vision2, 'scanner', session), \
                patch.object(cv2, 'VideoCapture', return_value=camera) as capture, \
                patch.object(cv2, 'imshow') as show, patch.object(cv2, 'destroyAllWindows'), \
                patch.object(cv2, 'moveWindow'), \
                patch.object(cv2, 'waitKey', side_effect=[-1, -1, ord('x')]), \
                patch.object(cv2, 'getWindowProperty', return_value=1):
            vision2.grab_colors(1, cv2.CAP_DSHOW, show_masks=False)
        capture.assert_called_once_with(1, cv2.CAP_DSHOW)
        camera.release.assert_called_once()
        self.assertTrue(all(call.args[0] != 'Cube Faces' for call in show.call_args_list))
        self.assertEqual(session.snapshot()['faces']['white'],
                         ('red', 'green', 'blue', 'orange', 'white', 'yellow', 'blue', 'red', 'green'))

    def test_getcolor_clips_image_edges_without_unsigned_overflow(self):
        """Input: sample at an image corner. Output: white and no arithmetic warning."""
        hsv = np.zeros((100, 100, 3), dtype=float)
        hsv[:, :, 2] = 220
        with patch.multiple(vision2, hsv=hsv, width=100, height=100, create=True):
            with warnings.catch_warnings():
                warnings.simplefilter('error', RuntimeWarning)
                _, color = vision2.getcolor(np.array([0, 0], dtype=np.uint16))
        self.assertEqual(color, 'white')

    def test_getcolors_requires_nine_distinct_positions(self):
        """Input: candidate geometry. Output: accept full grid and reject missing cells."""
        hsv = np.zeros((100, 100, 3), dtype=float)
        hsv[:, :, 2] = 220
        corners = [np.array(p) for p in ((20, 20), (60, 20), (20, 60), (60, 60))]
        edges = [np.array(p) for p in ((40, 20), (20, 40), (60, 40), (40, 60))]
        with patch.multiple(vision2, hsv=hsv, width=100, height=100, create=True):
            _, colors = vision2.getcolors(corners, edges, [], [], np.array([40, 40]))
            self.assertEqual(colors, [['white'] * 3 for _ in range(3)])
            self.assertEqual(len(vision2.face_centers), 9)
            _, colors = vision2.getcolors(corners, edges[:3] + edges[:1], [], [], np.array([40, 40]))
            self.assertEqual(colors, [])

    def test_preview_preserves_boxes_and_center_circles(self):
        """Input: full face and snapshot. Output: the existing annotated camera style."""
        scanner = FaceScanner()
        scanner.update([['white'] * 3 for _ in range(3)], 0)
        scanner.save_current()
        centers = [np.array([100+x*50, 100+y*50]) for y in range(3) for x in range(3)]
        boxes = [np.asarray([[x-18, y-18], [x+18, y-18], [x+18, y+18], [x-18, y+18]], dtype=np.float32)
                 for x, y in centers]
        hsv = np.zeros((300, 400, 3), dtype=float)
        hsv[:, :, 2] = 220
        with patch.multiple(vision2, face_centers=centers, face_boxes=boxes,
                            hsv=hsv, width=400, height=300, create=True):
            frame = np.zeros((300, 400, 3), dtype=np.uint8)
            annotated = vision2.draw_scan_overlay(frame, [['white'] * 3 for _ in range(3)], scanner.snapshot())
        self.assertGreater(np.count_nonzero(annotated[75:225]), 0)


if __name__ == '__main__':
    unittest.main()
