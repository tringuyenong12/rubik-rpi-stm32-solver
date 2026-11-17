"""Stabilize annotation labels without delaying the camera or saving stale faces."""
from collections import Counter, deque
from math import ceil
from time import monotonic

import cv2
import numpy as np


class StableScanPreview:
    def __init__(self, hold_seconds=.18, motion_threshold=8):
        self.hold_seconds = hold_seconds
        self.motion_threshold = motion_threshold
        self.reset()

    def reset(self):
        self.history = deque(maxlen=5)
        self.colors, self.boxes = [], []
        self.last_valid = -float('inf')
        self.previous_image = None
        self.key = None

    def _clear_labels(self):
        self.history.clear()
        self.colors, self.boxes = [], []

    def update(self, frame, colors, boxes, roi, now=None):
        now = monotonic() if now is None else now
        key = (frame.shape[:2], tuple(np.asarray(roi).ravel()))
        if self.key != key:
            self.reset()
            self.key = key
        points = np.asarray(roi)
        if points.shape == (4, 2):
            x1, y1 = np.floor(points.min(axis=0)).astype(int)
            x2, y2 = np.ceil(points.max(axis=0)).astype(int)
        else:
            x1, y1, x2, y2 = roi
        height, width = frame.shape[:2]
        crop = frame[max(0, y1):min(height, y2), max(0, x1):min(width, x2)]
        if crop.size == 0:
            self.reset()
            return [], []
        small = cv2.resize(crop, (48, 48), interpolation=cv2.INTER_AREA)
        moving = (self.previous_image is not None
                  and np.mean(cv2.absdiff(small, self.previous_image)) > self.motion_threshold)
        self.previous_image = small
        valid = len(colors) == 3 and all(len(row) == 3 for row in colors) and len(boxes) == 9
        if moving or now-self.last_valid > self.hold_seconds:
            self._clear_labels()
        if not valid:
            return self.colors, self.boxes
        face = tuple(color for row in colors for color in row)
        if self.colors:
            previous = tuple(color for row in self.colors for color in row)
            changes = sum(a != b for i, (a, b) in enumerate(zip(face, previous)) if i != 4)
            if changes >= 3:
                self._clear_labels()
        self.last_valid = now
        self.history.append(face)
        if len(self.history) >= 3:
            votes = [Counter(column).most_common(1)[0] for column in zip(*self.history)]
            if all(count >= max(3, ceil(len(self.history)*.8)) for _, count in votes):
                voted = tuple(color for color, _ in votes)
                grid = [list(voted[row:row+3]) for row in (0, 3, 6)]
                if grid != self.colors:
                    self.colors = grid
                    self.boxes = [np.asarray(box).copy() for box in boxes]
        return self.colors, self.boxes
