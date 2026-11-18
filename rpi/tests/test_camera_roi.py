"""Check that background stickers cannot enter ROI detection or saved settings."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from rubik_robot.vision.roi import CameraROI
from twophase import vision2


class TestCameraROI(unittest.TestCase):
    def test_reverse_corner_clicks_do_not_mirror_the_face(self):
        with TemporaryDirectory() as directory:
            roi = CameraROI(Path(directory) / 'roi.json')
            roi.load(0)
            roi.bounds((480, 640, 3))
            roi.picking = []
            # Left, bottom, right, top used to reflect the grid.
            for x, y in ((100, 240), (300, 440), (500, 240), (300, 40)):
                roi.mouse(cv2.EVENT_LBUTTONDOWN, x, y, 0, None)
            expected = ((100, 240), (300, 40), (500, 240), (300, 440))
            np.testing.assert_allclose(roi.selection((480, 640, 3)), expected, atol=.001)
            roi.load(0)
            np.testing.assert_allclose(roi.selection((480, 640, 3)), expected, atol=.001)

    def test_legacy_reversed_settings_are_loaded_without_reflection(self):
        import json
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'roi.json'
            path.write_text(json.dumps({'0': {'corners': [[.2, .5], [.5, .9], [.8, .5], [.5, .1]]}}))
            roi = CameraROI(path)
            roi.load(0)
            self.assertGreater(cv2.contourArea(np.float32(roi.corners), oriented=True), 0)
            np.testing.assert_allclose(roi.corners[0], (.2, .5))

    def test_cached_polygon_shading_preserves_stickers_and_updates_after_roi_changes(self):
        roi = CameraROI()
        roi.corners = ((.4, .3), (.6, .3), (.6, .7), (.4, .7))
        frame = np.full((480, 640, 3), (90, 150, 210), dtype=np.uint8)
        roi.draw(frame)
        np.testing.assert_array_equal(frame[240, 320], [90, 150, 210])
        np.testing.assert_array_equal(frame[100, 10], [30, 50, 70])
        roi.corners = ((.65, .3), (.85, .3), (.85, .7), (.65, .7))
        frame[:] = (90, 150, 210)
        roi.draw(frame)
        np.testing.assert_array_equal(frame[240, 320], [30, 50, 70])
        np.testing.assert_array_equal(frame[240, 480], [90, 150, 210])
        bigger = np.full((960, 1280, 3), (90, 150, 210), dtype=np.uint8)
        roi.draw(bigger)
        np.testing.assert_array_equal(bigger[480, 960], [90, 150, 210])

    def test_skipping_debug_masks_does_not_change_colors_or_sample_geometry(self):
        frame = np.full((480, 640, 3), 20, dtype=np.uint8)
        for row in range(3):
            for col in range(3):
                cv2.rectangle(frame, (170+col*100, 90+row*100), (260+col*100, 180+row*100), (0, 140, 255), -1)
        corners = ((165, 85), (465, 85), (465, 385), (165, 385))
        samples, colors = vision2.detect_face(frame, corners)
        centers = np.asarray(vision2.face_centers).copy()
        fast_samples, fast_colors = vision2.detect_face(frame, corners, include_masks=False)
        self.assertTrue(colors)
        self.assertEqual(fast_colors, colors)
        np.testing.assert_allclose(fast_samples, samples)
        np.testing.assert_allclose(vision2.face_centers, centers)

    def test_uint8_saturated_red_does_not_overflow_hue_weights(self):
        hsv = np.full((40, 40, 3), (179, 255, 220), dtype=np.uint8)
        hsv[:, :20, 0] = 1
        with patch.multiple(vision2, hsv=hsv, width=40, height=40, create=True):
            sample, color = vision2.getcolor((20, 20), radius=18)
        self.assertEqual(color, 'red')
        self.assertEqual(sample[1], 255)

    def test_four_corners_rectify_a_diamond_face_and_reject_a_missing_sticker(self):
        canonical = np.full((360, 360, 3), 20, dtype=np.uint8)
        palette = [(0, 0, 220), (0, 170, 0), (220, 70, 0), (0, 140, 255),
                   (240, 240, 240), (0, 230, 255), (220, 70, 0), (0, 0, 220), (0, 170, 0)]
        for index, color in enumerate(palette):
            x, y = index % 3*120, index // 3*120
            cv2.rectangle(canonical, (x+12, y+12), (x+108, y+108), color, -1)
        source = np.float32([[0, 0], [359, 0], [359, 359], [0, 359]])
        corners = np.float32([[310, 45], [500, 240], [295, 430], [110, 225]])
        transform = cv2.getPerspectiveTransform(source, corners)
        frame = cv2.warpPerspective(canonical, transform, (640, 480))
        expected = [['red', 'green', 'blue'], ['orange', 'white', 'yellow'], ['blue', 'red', 'green']]
        self.assertEqual(vision2.detect_face(frame, corners)[1], expected)
        original = cv2.perspectiveTransform(np.float32([[[60, 60]]]), transform)[0, 0]
        np.testing.assert_allclose(vision2.face_centers[0], original, atol=.1)
        self.assertEqual(vision2.color_mask.shape, frame.shape[:2])
        self.assertFalse(np.any(vision2.color_mask[:, :100]))
        for dx, dy in ((-8, 0), (8, 0), (0, -8), (0, 8), (-8, -8), (8, 8)):
            with self.subTest(dx=dx, dy=dy):
                shifted = cv2.warpAffine(frame, np.float32([[1, 0, dx], [0, 1, dy]]), (640, 480))
                self.assertEqual(vision2.detect_face(shifted, corners)[1], expected)
        canonical[240:360, 240:360] = 20
        frame = cv2.warpPerspective(canonical, transform, (640, 480))
        self.assertEqual(vision2.detect_face(frame, corners)[1], [])
        self.assertEqual(vision2.face_centers, [])

    def test_face_search_follows_translation_rotation_and_small_size_changes(self):
        canonical = np.full((360, 360, 3), 20, dtype=np.uint8)
        palette = [(0, 0, 220), (0, 170, 0), (220, 70, 0), (0, 140, 255),
                   (240, 240, 240), (0, 230, 255), (220, 70, 0), (0, 0, 220), (0, 170, 0)]
        for index, color in enumerate(palette):
            x, y = index % 3*120, index // 3*120
            cv2.rectangle(canonical, (x+12, y+12), (x+108, y+108), color, -1)
        source = np.float32([[0, 0], [359, 0], [359, 359], [0, 359]])
        corners = np.float32([[310, 45], [500, 240], [295, 430], [110, 225]])
        frame = cv2.warpPerspective(canonical, cv2.getPerspectiveTransform(source, corners), (640, 480))
        expected = [['red', 'green', 'blue'], ['orange', 'white', 'yellow'], ['blue', 'red', 'green']]
        for dx, dy, angle, scale in ((30, 12, 0, 1), (-24, -15, 0, 1),
                                      (14, 8, 6, .94), (-12, 8, -5, 1.05)):
            with self.subTest(dx=dx, dy=dy, angle=angle, scale=scale):
                motion = cv2.getRotationMatrix2D((305, 238), angle, scale)
                motion[:, 2] += (dx, dy)
                moved = cv2.warpAffine(frame, motion, (640, 480), borderValue=(20, 20, 20))
                self.assertEqual(vision2.detect_face(moved, corners, include_masks=False)[1], expected)

    def test_red_hue_wrap_does_not_average_to_blue(self):
        hsv = np.full((40, 40, 3), (179, 200, 220), dtype=float)
        hsv[:, :20, 0] = 1
        with patch.multiple(vision2, hsv=hsv, width=40, height=40, create=True):
            self.assertEqual(vision2.getcolor((20, 20), radius=18)[1], 'red')

    def test_polygon_settings_survive_reload_and_resolution_change(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'roi.json'
            roi = CameraROI(path)
            roi.load(1)
            roi.corners = ((.5, .1), (.8, .5), (.5, .9), (.2, .5))
            roi.save()
            restored = CameraROI(path)
            restored.load(1)
            np.testing.assert_allclose(restored.selection((1000, 2000, 3)),
                                       ((1000, 100), (1600, 500), (1000, 900), (400, 500)), atol=.001)

    def test_background_grid_is_ignored_and_geometry_stays_in_frame_coordinates(self):
        frame = np.full((480, 640, 3), 20, dtype=np.uint8)
        for row in range(3):
            for col in range(3):
                cv2.rectangle(frame, (15 + col*32, 50 + row*32),
                              (39 + col*32, 74 + row*32), (0, 0, 230), -1)
        roi = (170, 110, 450, 390)
        self.assertEqual(vision2.detect_face(frame, roi)[1], [])
        self.assertEqual(vision2.sticker_boxes, [])
        for row in range(3):
            for col in range(3):
                cv2.rectangle(frame, (200 + col*65, 140 + row*65),
                              (250 + col*65, 190 + row*65), (0, 180, 0), -1)
        self.assertEqual(vision2.detect_face(frame, roi)[1], [['green']*3 for _ in range(3)])
        np.testing.assert_allclose(vision2.face_centers[0], (225, 165), atol=2)
        self.assertEqual(vision2.hsv.shape, frame.shape)
        self.assertEqual(vision2.color_mask.shape, frame.shape[:2])
        self.assertFalse(np.any(vision2.color_mask[:, :170]))
        self.assertEqual(vision2.getcolor(vision2.face_centers[0])[1], 'green')

    def test_drag_persists_per_camera_and_scales_with_frame(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'roi.json'
            roi = CameraROI(path)
            roi.load(1)
            roi.bounds((480, 640, 3))
            roi.mouse(cv2.EVENT_LBUTTONDOWN, 450, 390, 0, None)
            roi.mouse(cv2.EVENT_LBUTTONUP, 170, 110, 0, None)
            restored = CameraROI(path)
            restored.load(1)
            self.assertEqual(restored.bounds((960, 1280, 3)), (340, 220, 900, 780))
            restored.load(0)
            self.assertEqual(restored.bounds((480, 640, 3)), (128, 48, 512, 432))

    def test_preview_does_not_change_pixels_inside_roi(self):
        roi = CameraROI()
        frame = np.full((480, 640, 3), 180, dtype=np.uint8)
        roi.draw(frame)
        self.assertTrue(np.all(frame[100:400, 150:490] == 180))
        self.assertTrue(np.all(frame[60:400, :120] == 60))


if __name__ == '__main__':
    unittest.main()
