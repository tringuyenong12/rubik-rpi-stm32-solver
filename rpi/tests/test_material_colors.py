"""Read the sticker material rather than unstable red/orange or white glare."""
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from twophase import vision2, vision_params


class TestMaterialColors(unittest.TestCase):
    def test_measured_c270_red_glare_and_orange_remain_separate(self):
        # Live C270 samples: red highlight H=7-8, orange H=10-11.
        for hue, saturation, expected in ((7, 84, 'red'), (8, 84, 'red'),
                                           (10, 255, 'orange'), (11, 255, 'orange')):
            with self.subTest(hue=hue):
                hsv = np.full((120, 120, 3), (hue, saturation, 152), dtype=np.float32)
                with patch.multiple(vision2, hsv=hsv, width=120, height=120, create=True), \
                        patch.object(vision_params, 'sat_W', 35), \
                        patch.object(vision_params, 'orange_L', 9):
                    self.assertEqual(vision2.getcolor((60, 60), radius=18)[1], expected)

    def classify(self, hsv):
        with patch.multiple(vision2, hsv=hsv, width=80, height=80, create=True), \
                patch.object(vision_params, 'sat_W', 35), patch.object(vision_params, 'orange_L', 6):
            return vision2.getcolor((40, 40), radius=18)

    def test_red_is_stable_when_its_glossy_center_crosses_the_orange_boundary(self):
        for hue in (5.5, 5.9, 6.1, 6.5, 7.0):
            with self.subTest(center_hue=hue):
                hsv = np.full((80, 80, 3), (1, 180, 160), dtype=np.float32)
                hsv[22:58, 22:58] = (hue, 65, 210)
                sample, color = self.classify(hsv)
                self.assertEqual(color, 'red')
                self.assertLess(sample[0], 3)

    def test_blue_and_orange_material_survive_a_white_specular_center(self):
        for hue, expected in ((110, 'blue'), (9, 'orange')):
            with self.subTest(color=expected):
                hsv = np.full((80, 80, 3), (hue, 180, 180), dtype=np.float32)
                hsv[22:58, 22:58] = (0, 0, 255)
                self.assertEqual(self.classify(hsv)[1], expected)

    def test_large_glare_recovers_material_inside_the_same_sticker(self):
        for hue, expected in ((110, 'blue'), (9, 'orange'), (33, 'yellow')):
            with self.subTest(color=expected):
                hsv = np.full((120, 120, 3), (hue, 180, 190), dtype=np.float32)
                cv2.circle(hsv, (60, 60), 30, (0, 0, 255), -1)
                with patch.multiple(vision2, hsv=hsv, width=120, height=120, create=True), \
                        patch.object(vision_params, 'sat_W', 35):
                    self.assertEqual(vision2.getcolor((60, 60), radius=18)[1], expected)

    def test_grid_with_large_center_reflection_still_requires_all_nine_stickers(self):
        hsv = np.full((360, 360, 3), (110, 180, 190), dtype=np.uint8)
        cv2.circle(hsv, (180, 180), 30, (0, 0, 255), -1)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        with patch.object(vision_params, 'sat_W', 35):
            self.assertEqual(vision2._detect_calibrated_grid(frame)[1], [['blue']*3 for _ in range(3)])
            frame[240:360, 240:360] = 20
            self.assertEqual(vision2._detect_calibrated_grid(frame)[1], [])

    def test_red_circular_center_recovers_its_material_around_a_large_orange_glint(self):
        hsv = np.full((120, 120, 3), (2, 150, 130), dtype=np.float32)
        cv2.circle(hsv, (60, 60), 40, (9, 50, 190), -1)
        with patch.multiple(vision2, hsv=hsv, width=120, height=120, create=True), \
                patch.object(vision_params, 'sat_W', 35):
            sample, color = vision2.getcolor((60, 60), radius=18)
        self.assertEqual(color, 'red')
        self.assertTrue(vision2.center_color_confident(sample, color))

    def test_measured_orange_floor_rejects_dark_warm_occlusion(self):
        with patch.object(vision_params, 'orange_min_V', 110), \
                patch.object(vision_params, 'yellow_min_V', 110):
            hsv = np.full((80, 80, 3), (14, 160, 80), dtype=np.float32)
            self.assertEqual(self.classify(hsv)[1], '')
            hsv[:] = (30, 160, 80)
            self.assertEqual(self.classify(hsv)[1], '')
            hsv[:] = (9, 180, 180)
            self.assertEqual(self.classify(hsv)[1], 'orange')
            hsv[:] = (30, 180, 180)
            self.assertEqual(self.classify(hsv)[1], 'yellow')

    def test_peripheral_warm_material_cannot_replace_a_green_sticker(self):
        hsv = np.full((120, 120, 3), (14, 240, 90), dtype=np.float32)
        cv2.rectangle(hsv, (30, 30), (90, 90), (53, 160, 120), -1)
        with patch.multiple(vision2, hsv=hsv, width=120, height=120, create=True), \
                patch.object(vision_params, 'sat_W', 35):
            self.assertEqual(vision2.getcolor((60, 60), radius=18)[1], 'green')

    def test_washed_blue_center_recovers_a_sparse_lower_rim_without_lowering_white_threshold(self):
        hsv = np.full((120, 120, 3), (106, 37, 162), dtype=np.float32)
        yy, xx = np.mgrid[-60:60, -60:60]
        ring = ((xx*xx+yy*yy >= 40*40) & (xx*xx+yy*yy < 54*54) & (yy >= 0))
        hsv[ring] = (111, 90, 130)
        with patch.multiple(vision2, hsv=hsv, width=120, height=120, create=True), \
                patch.object(vision_params, 'sat_W', 35):
            sample, color = vision2.getcolor((60, 60), radius=18)
            self.assertEqual(color, 'blue')
            self.assertTrue(vision2.center_color_confident(sample, color))

    def test_weak_blue_tint_without_material_and_white_with_adjacent_blue_stay_uncertain(self):
        yy, xx = np.mgrid[-60:60, -60:60]
        ring = (xx*xx+yy*yy >= 40*40) & (xx*xx+yy*yy < 54*54)
        for central in ((110, 20, 180), (70, 8, 180)):
            with self.subTest(central=central):
                hsv = np.full((120, 120, 3), central, dtype=np.float32)
                if central[1] == 8:
                    hsv[ring & (xx < -25)] = (111, 90, 130)
                with patch.multiple(vision2, hsv=hsv, width=120, height=120, create=True), \
                        patch.object(vision_params, 'sat_W', 35):
                    self.assertIsNone(vision2.blue_glare_material((60, 60)))
                    self.assertNotEqual(vision2.getcolor((60, 60), radius=18)[1], 'blue')

    def test_full_grid_accepts_washed_blue_center_but_still_rejects_a_missing_cell(self):
        hsv = np.full((360, 360, 3), (111, 180, 150), dtype=np.uint8)
        yy, xx = np.mgrid[-60:60, -60:60]
        ring = ((xx*xx+yy*yy >= 40*40) & (xx*xx+yy*yy < 54*54) & (yy >= 0))
        hsv[120:240, 120:240] = (106, 34, 162)
        hsv[120:240, 120:240][ring] = (111, 90, 130)
        frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        with patch.object(vision_params, 'sat_W', 35):
            self.assertEqual(vision2._detect_calibrated_grid(frame)[1], [['blue']*3 for _ in range(3)])
            frame[240:360, 240:360] = 20
            self.assertEqual(vision2._detect_calibrated_grid(frame)[1], [])

    def test_uncertain_red_orange_boundary_is_not_forced_into_either_color(self):
        for hue in (5.8, 6.0, 6.2):
            hsv = np.full((80, 80, 3), (hue, 180, 180), dtype=np.float32)
            self.assertEqual(self.classify(hsv)[1], '')

    def test_fully_clipped_patch_is_not_committed_as_white(self):
        hsv = np.full((80, 80, 3), (0, 0, 255), dtype=np.float32)
        self.assertEqual(self.classify(hsv)[1], '')
        hsv[:] = (70, 8, 200)
        self.assertEqual(self.classify(hsv)[1], 'white')


if __name__ == '__main__':
    unittest.main()
