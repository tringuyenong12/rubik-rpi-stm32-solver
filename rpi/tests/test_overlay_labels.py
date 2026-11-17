"""A label on a rotated sticker must never appear on its neighbor."""
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from twophase import vision2


class TestOverlayLabels(unittest.TestCase):
    def test_blue_white_labels_remain_inside_their_rotated_stickers(self):
        canonical = np.float32([[0, 0], [359, 0], [359, 359], [0, 359]])
        diamond = np.float32([[300, 50], [480, 235], [292, 420], [112, 228]])
        transform = cv2.getPerspectiveTransform(canonical, diamond)
        boxes = []
        for row in range(3):
            for col in range(3):
                x, y = 60+120*col, 60+120*row
                points = np.float32([[[x-45, y-45], [x+45, y-45], [x+45, y+45], [x-45, y+45]]])
                boxes.append(cv2.perspectiveTransform(points, transform)[0])
        colors = [['green', 'green', 'blue'], ['white', 'blue', 'white'], ['yellow', 'blue', 'white']]
        state = {'progress': 0, 'current': (), 'faces': {}, 'message': 'Checking labels'}
        frame = np.full((480, 640, 3), 100, dtype=np.uint8)
        with patch.object(cv2, 'putText', wraps=cv2.putText) as draw_text:
            vision2.draw_scan_overlay(frame, colors, state, boxes_override=boxes)
        labels = [call for call in draw_text.call_args_list
                  if call.args[1] in ('green', 'blue', 'white', 'yellow')]
        self.assertEqual(len(labels), 9)
        for call, box, expected in zip(labels, boxes, [c for row in colors for c in row]):
            label, (x, y), scale = call.args[1], call.args[2], call.args[4]
            self.assertEqual(label, expected)
            (width, height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
            for point in ((x-2, y-height-2), (x+width+2, y-height-2),
                          (x+width+2, y+baseline+2), (x-2, y+baseline+2)):
                self.assertGreaterEqual(cv2.pointPolygonTest(box, point, True), .5)

    def test_tiny_sticker_omits_text_instead_of_drawing_over_another_cell(self):
        box = np.float32([[10, 10], [14, 10], [14, 14], [10, 14]])
        self.assertIsNone(vision2.sticker_label_layout(box, 'orange', (100, 100, 3)))


if __name__ == '__main__':
    unittest.main()
