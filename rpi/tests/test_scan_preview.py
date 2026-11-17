"""Stop annotation flicker while keeping motion and stale frames visible."""
import unittest

import numpy as np

from rubik_robot.vision.scan_preview import StableScanPreview


class TestScanPreview(unittest.TestCase):
    def setUp(self):
        self.preview = StableScanPreview()
        self.frame = np.full((120, 120, 3), 60, dtype=np.uint8)
        self.roi = (0, 0, 120, 120)
        self.grid = [['orange']*3 for _ in range(3)]
        self.boxes = [np.float32([[x, y], [x+20, y], [x+20, y+20], [x, y+20]])
                      for y in (10, 45, 80) for x in (10, 45, 80)]

    def show(self, grid, now, frame=None, boxes=None):
        return self.preview.update(self.frame if frame is None else frame, grid,
                                   self.boxes if boxes is None else boxes, self.roi, now=now)

    def acquire(self):
        self.assertEqual(self.show(self.grid, 0)[0], [])
        self.assertEqual(self.show(self.grid, .03)[0], [])
        self.assertEqual(self.show(self.grid, .06)[0], self.grid)

    def test_one_noisy_center_or_missed_frame_does_not_flash_labels(self):
        self.acquire()
        noise = [['orange']*3 for _ in range(3)]
        noise[1][1] = 'red'
        self.assertEqual(self.show(noise, .09)[0], self.grid)
        self.assertEqual(self.show([], .12, boxes=[])[0], self.grid)
        self.assertEqual(self.show(self.grid, .15)[0], self.grid)

    def test_expired_detection_is_removed_instead_of_freezing_old_labels(self):
        self.acquire()
        self.assertEqual(self.show([], .3, boxes=[])[0], [])

    def test_actual_image_motion_immediately_removes_old_face_labels(self):
        self.acquire()
        moving = np.full_like(self.frame, 200)
        self.assertEqual(self.show([], .09, frame=moving, boxes=[])[0], [])

    def test_new_face_reacquires_after_three_agreeing_frames(self):
        self.acquire()
        new_face = [['blue']*3 for _ in range(3)]
        self.assertEqual(self.show(new_face, .09)[0], [])
        self.assertEqual(self.show(new_face, .12)[0], [])
        self.assertEqual(self.show(new_face, .15)[0], new_face)

    def test_placement_retry_does_not_make_same_face_boxes_jump(self):
        self.acquire()
        _, boxes = self.show(self.grid, .09, boxes=[box+16 for box in self.boxes])
        np.testing.assert_array_equal(boxes, self.boxes)

    def test_roi_change_clears_previous_labels(self):
        self.acquire()
        self.roi = (10, 10, 110, 110)
        self.assertEqual(self.show(self.grid, .09)[0], [])


if __name__ == '__main__':
    unittest.main()
