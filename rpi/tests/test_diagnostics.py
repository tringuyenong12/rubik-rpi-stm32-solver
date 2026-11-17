"""Keep diagnostic runs independent and camera operation alive on disk failures."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from rubik_robot.vision.diagnostics import FrameRecorder


class TestDiagnostics(unittest.TestCase):
    def setUp(self):
        self.frame = np.full((24, 24, 3), 100, dtype=np.uint8)
        self.colors = [['blue']*3 for _ in range(3)]
        self.roi = (0, 0, 24, 24)

    def record(self, recorder):
        return recorder.record(self.frame, [], self.colors, self.roi,
                               state={'faces': ['blue']}, displayed=self.colors)

    def test_reopened_directory_preserves_images_and_separates_logs(self):
        with TemporaryDirectory() as folder:
            first = FrameRecorder(folder, interval=0)
            self.assertTrue(self.record(first))
            old_image = (first.directory/'frame_0000.png').read_bytes()
            old_log = (first.directory/'frames.jsonl').read_text()
            second = FrameRecorder(folder, interval=0)
            self.assertNotEqual(first.directory, second.directory)
            self.frame[:] = 200
            self.assertTrue(self.record(second))
            self.assertEqual((first.directory/'frame_0000.png').read_bytes(), old_image)
            self.assertEqual((first.directory/'frames.jsonl').read_text(), old_log)
            self.assertNotEqual((second.directory/'frame_0000.png').read_bytes(), old_image)
            self.assertEqual(json.loads((second.directory/'frames.jsonl').read_text())['displayed'], self.colors)

    def test_image_left_by_an_interrupted_log_write_is_preserved(self):
        with TemporaryDirectory() as folder:
            image = Path(folder)/'frame_0000.png'
            image.write_bytes(b'previous capture')
            recorder = FrameRecorder(folder, interval=0)
            self.assertNotEqual(recorder.directory, Path(folder))
            self.assertTrue(self.record(recorder))
            self.assertEqual(image.read_bytes(), b'previous capture')

    def test_failed_image_write_disables_recording_without_raising_or_retrying(self):
        with TemporaryDirectory() as folder:
            recorder = FrameRecorder(folder, interval=0)
            with patch('rubik_robot.vision.diagnostics.cv2.imwrite', return_value=False) as write, \
                    self.assertLogs('rubik_robot.vision.diagnostics', level='WARNING'):
                self.assertFalse(self.record(recorder))
                self.assertFalse(self.record(recorder))
            write.assert_called_once()
            self.assertTrue(recorder.error)
            self.assertEqual(recorder.count, 0)

    def test_full_log_disk_does_not_raise_and_the_next_run_does_not_overwrite_the_orphan(self):
        with TemporaryDirectory() as folder:
            recorder = FrameRecorder(folder, interval=0)
            with patch.object(Path, 'open', side_effect=OSError('disk full')), \
                    self.assertLogs('rubik_robot.vision.diagnostics', level='WARNING'):
                self.assertFalse(self.record(recorder))
            image = recorder.directory/'frame_0000.png'
            self.assertTrue(image.exists())
            self.assertEqual(recorder.error, 'disk full')
            next_run = FrameRecorder(folder, interval=0)
            self.assertNotEqual(next_run.directory, recorder.directory)

    def test_reaching_frame_limit_is_reported_and_preserves_the_last_capture(self):
        with TemporaryDirectory() as folder:
            recorder = FrameRecorder(folder, interval=0, limit=1)
            with self.assertLogs('rubik_robot.vision.diagnostics', level='WARNING'):
                self.assertTrue(self.record(recorder))
            self.assertFalse(self.record(recorder))
            self.assertEqual(recorder.count, 1)
            self.assertEqual(len((recorder.directory/'frames.jsonl').read_text().splitlines()), 1)
