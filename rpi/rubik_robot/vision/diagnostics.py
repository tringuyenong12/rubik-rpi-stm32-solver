"""Bounded raw-frame recording for repeatable camera recognition checks."""
import json
import logging
import tempfile
from pathlib import Path
from time import monotonic

import cv2
import numpy as np


class FrameRecorder:
    def __init__(self, directory, interval=.25, limit=2400):
        if interval < 0 or limit < 1:
            raise ValueError('Diagnostic interval must be nonnegative and limit must be positive')
        self.directory = Path(directory)
        self.error = ''
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            if ((self.directory / 'frames.jsonl').exists()
                    or next(self.directory.glob('frame_*.png'), None) is not None):
                # Preserve both the previous log and any image left before a
                # write failure. Each reopened run gets a separate session.
                self.directory = Path(tempfile.mkdtemp(prefix='session_', dir=self.directory))
        except OSError as error:
            self._failed(error)
        self.interval, self.limit = interval, limit
        self.last = -float('inf')
        self.count = 0

    def _failed(self, error):
        self.error = str(error)
        logging.getLogger(__name__).warning('Diagnostic recording stopped: %s', error)

    def record(self, frame, samples, colors, roi, rejection='', state=None, displayed=None):
        now = monotonic()
        if self.error or now - self.last < self.interval or self.count >= self.limit:
            return False
        filename = f'frame_{self.count:04d}.png'
        try:
            if not cv2.imwrite(str(self.directory / filename), frame):
                raise OSError(f'Cannot save diagnostic image: {filename}')
            item = {'frame': filename, 'time': now, 'roi': roi, 'colors': colors,
                    'hsv': np.asarray(samples).tolist(), 'rejection': rejection,
                    'scan': state, 'displayed': displayed}
            with (self.directory / 'frames.jsonl').open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(item) + '\n')
        except (OSError, cv2.error) as error:
            # A full/unavailable diagnostic disk must not stop camera scanning.
            self._failed(error)
            return False
        self.last = now
        self.count += 1
        if self.count == self.limit:
            logging.getLogger(__name__).warning('Diagnostic frame limit reached (%s): %s',
                                                self.limit, self.directory)
        return True
