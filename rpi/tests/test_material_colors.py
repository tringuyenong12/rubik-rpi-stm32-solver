"""Read the sticker material rather than unstable red/orange or white glare."""
import unittest
from unittest.mock import patch

import numpy as np

from twophase import vision2, vision_params


class TestMaterialColors(unittest.TestCase):
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
