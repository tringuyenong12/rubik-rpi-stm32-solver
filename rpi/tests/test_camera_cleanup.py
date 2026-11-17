"""Optional report failures must not prevent releasing the camera and windows."""
from threading import Event
import unittest
from unittest.mock import Mock, patch

from twophase import vision2


class TestCameraCleanup(unittest.TestCase):
    def test_performance_disk_failure_still_releases_camera_sets_stop_and_closes_windows(self):
        camera = Mock()
        camera.isOpened.return_value = False
        performance = Mock()
        performance.finish.side_effect = OSError('disk full')
        stopped = Event()
        with patch.object(vision2.cv2, 'VideoCapture', return_value=camera), \
                patch.object(vision2.cv2, 'destroyAllWindows') as close, \
                patch.object(vision2.camera_roi, 'load'), \
                patch.object(vision2, 'performance_recorder', performance), \
                patch.object(vision2, 'camera_stop', stopped), patch('builtins.print'):
            vision2.grab_colors(0, show_masks=False)
        camera.release.assert_called_once()
        close.assert_called_once()
        self.assertTrue(stopped.is_set())
        self.assertIn('Cannot open camera', vision2.camera_error)
