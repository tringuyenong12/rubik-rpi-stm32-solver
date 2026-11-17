"""Bounded raw-frame recording for repeatable camera recognition checks."""
import json
from pathlib import Path
from time import monotonic

import cv2
import numpy as np


class FrameRecorder:
    def __init__(self, directory, interval=.25, limit=480):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.interval, self.limit = interval, limit
        self.last = -float('inf')
        self.count = 0

    def record(self, frame, samples, colors, roi):
        now = monotonic()
        if now - self.last < self.interval or self.count >= self.limit:
            return
        self.last = now
        filename = f'frame_{self.count:04d}.png'
        if not cv2.imwrite(str(self.directory / filename), frame):
            return
        item = {'frame': filename, 'time': now, 'roi': roi, 'colors': colors,
                'hsv': np.asarray(samples).tolist()}
        with (self.directory / 'frames.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(item) + '\n')
        self.count += 1
