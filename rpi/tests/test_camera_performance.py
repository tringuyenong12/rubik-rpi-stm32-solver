"""Check steady-preview reporting and deferred evidence recording."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from rubik_robot.vision.performance import CameraPerformance


class TestCameraPerformance(unittest.TestCase):
    def test_metrics_are_written_only_at_shutdown_with_correct_steady_fps(self):
        with TemporaryDirectory() as directory:
            target = Path(directory) / 'metrics.json'
            recorder = CameraPerformance(target)
            grid = [['red']*3 for _ in range(3)]
            state = {'faces': {}, 'message': 'Hold red still'}
            samples = np.full((3, 3, 3), (0, 180, 200), dtype=np.float32)
            for index in range(120):
                start = 100+index/30
                if index == 100:
                    state = {'faces': {'red': ('red',)*9}, 'message': 'Saved red'}
                raw = [['orange']*3 for _ in range(3)] if index in (100, 101) else grid
                recorder.record(start, start+.02, start+.024, start+.025, start+.03, raw, state, samples,
                                preview_colors=grid)
            self.assertFalse(target.exists())
            recorder.finish()
            result = json.loads(target.read_text(encoding='utf-8'))
            self.assertEqual(result['summary']['total_frames'], 120)
            self.assertAlmostEqual(result['summary']['fps'], 30, places=5)
            self.assertEqual(result['summary']['intervals_over_50ms'], 0)
            self.assertEqual(result['summary']['raw_label_changes'], 2)
            self.assertEqual(result['summary']['display_label_changes'], 0)
            self.assertEqual(len(result['summary']['saved_events']), 1)
            self.assertEqual(result['summary']['saved_events'][0]['centers'], ['red'])
            self.assertEqual(result['timeline'][0]['hsv'][1][1], [0, 180, 200])


if __name__ == '__main__':
    unittest.main()
