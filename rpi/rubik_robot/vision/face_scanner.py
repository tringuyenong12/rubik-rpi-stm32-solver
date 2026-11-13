"""Collect stable camera faces by center color for the desktop client."""

from collections import Counter, deque
from threading import Lock
from time import monotonic
import numpy as np


COLORS = ("yellow", "green", "red", "white", "blue", "orange")


class FaceScanner:
    """Input: successive 3x3 color grids. Output: six center-keyed faces."""

    def __init__(self, stable_seconds=0.18, min_samples=4):
        """Input: hold duration and frame count. Output: an empty scan session."""
        self.stable_seconds = stable_seconds
        self.min_samples = min_samples
        self.lock = Lock()
        self.enabled = True
        self.faces = {}
        self.hsv_faces = {}
        self.hsv_observations = deque(maxlen=max(7, min_samples))
        self.revision = 0
        self.current = ()
        self.current_hsv = None
        self.pending = ()
        self.started = 0.0
        self.samples = 0
        self.observations = deque(maxlen=max(7, min_samples))
        self.last_valid = 0.0
        self.progress = 0
        self.message = "Show a face and hold still"

    def update(self, grid, now=None, hsv_grid=None):
        """Input: detected grid and optional clock. Output: update session state."""
        now = monotonic() if now is None else now
        valid = len(grid) == 3 and all(len(row) == 3 for row in grid)
        face = tuple(color for row in grid for color in row) if valid else ()
        if any(color not in COLORS for color in face):
            face = ()
        numeric = np.asarray(hsv_grid, dtype=float) if hsv_grid is not None else np.asarray([])
        sample = numeric.reshape(9, 3) if numeric.shape == (3, 3, 3) and np.all(np.isfinite(numeric)) else None
        with self.lock:
            self.current = face
            self.current_hsv = sample if face else None
            if not face:
                if now - self.last_valid > 0.25:
                    self._clear_hold()
                self.message = "Looking for all 9 stickers"
                return
            if not self.enabled:
                self.message = "Auto scan paused"
                return
            center = face[4]
            if center in self.faces:
                self._clear_hold()
                self.message = f"{center}: already saved - show another face"
                if len(self.faces) == 6:
                    self.message = self._count_summary()
                return
            if not self.pending or center != self.pending[4]:
                self._clear_hold()
                self.pending, self.started, self.samples = face, now, 0
            self.last_valid = now
            self.observations.append(face)
            self.hsv_observations.append(sample)
            self.samples = len(self.observations)
            self.progress = min(99, int(100 * self.samples / self.min_samples))
            self.message = f"Hold {center} still"
            if self.samples < self.min_samples or now - self.started < self.stable_seconds:
                return
            votes = [Counter(column).most_common(1)[0] for column in zip(*self.observations)]
            if any(count / self.samples < 0.8 for _, count in votes):
                self.message = f"Checking {center} colors"
                return
            voted_face = tuple(color for color, _ in votes)
            samples = [sample for sample in self.hsv_observations if sample is not None]
            numeric_face = self._median_hsv(samples)
            if self._save_face(voted_face, numeric_face):
                self._clear_hold()
                self.progress = 100

    def _clear_hold(self):
        """Input: locked session. Output: clear the current voting window."""
        self.pending, self.samples, self.progress = (), 0, 0
        self.observations.clear()
        self.hsv_observations.clear()

    def _median_hsv(self, samples):
        """Input: HSV frame samples. Output: median S/V with circular mean hue."""
        if not samples:
            return None
        values = np.asarray(samples)
        result = np.median(values, axis=0)
        angles = values[:, :, 0] * np.pi / 90
        result[:, 0] = (np.arctan2(np.sin(angles).mean(axis=0), np.cos(angles).mean(axis=0)) % (2*np.pi)) * 90 / np.pi
        return result

    def _save_face(self, face, samples=None):
        """Input: flat face/HSV samples while locked. Output: save, then report global counts."""
        self.faces[face[4]] = face
        if samples is not None:
            self.hsv_faces[face[4]] = tuple(tuple(float(value) for value in row) for row in samples)
        else:
            self.hsv_faces.pop(face[4], None)
        self.revision += 1
        self.message = f"Saved {face[4]} ({len(self.faces)}/6)"
        if len(self.faces) == 6:
            self.message = self._count_summary()
        return True

    def _count_summary(self):
        """Input: locked six-face state. Output: persistent global color-count feedback."""
        counts = Counter(color for saved in self.faces.values() for color in saved)
        wrong = ', '.join(f'{color}={counts[color]}' for color in COLORS if counts[color] != 9)
        return f'6/6 saved - checking colors ({wrong})' if wrong else '6/6 saved - checking cube'

    def save_current(self):
        """Input: none. Output: manually save the latest valid face, returning success."""
        with self.lock:
            if not self.current:
                return False
            return self._save_face(self.current, self.current_hsv)

    def edit(self, center, index, color):
        """Input: saved sticker/color. Output: apply a manual label correction, retaining center samples."""
        if center not in COLORS or color not in COLORS or index not in range(9) or index == 4:
            return
        with self.lock:
            if center in self.faces:
                values = list(self.faces[center])
                values[index] = color
                self._save_face(tuple(values), self.hsv_faces.get(center))

    def set_verified_faces(self, faces):
        """Input: a confirmed six-face model. Output: synchronize editor state after guidance."""
        with self.lock:
            self.faces = {center: tuple(values) for center, values in faces.items()}
            self.hsv_faces.clear()
            self.revision += 1
            self._clear_hold()
            self.message = 'Verified solved cube'

    def rotate(self, center):
        """Input: saved center color. Output: rotate its grid 90 degrees clockwise."""
        with self.lock:
            if center in self.faces:
                face = self.faces[center]
                self.faces[center] = tuple(
                    face[(2 - col) * 3 + row]
                    for row in range(3)
                    for col in range(3)
                )
                if center in self.hsv_faces:
                    samples = self.hsv_faces[center]
                    self.hsv_faces[center] = tuple(samples[(2-col)*3+row] for row in range(3) for col in range(3))
                self.revision += 1

    def snapshot(self):
        """Input: none. Output: thread-safe copies of faces, preview and status."""
        with self.lock:
            return {
                "faces": dict(self.faces),
                "current": self.current,
                "enabled": self.enabled,
                "message": self.message,
                "progress": self.progress,
                "hsv_faces": dict(self.hsv_faces),
                "revision": self.revision,
            }

    def set_enabled(self, enabled):
        """Input: auto-scan flag. Output: pause/resume with a fresh hold timer."""
        with self.lock:
            self.enabled = bool(enabled)
            self._clear_hold()

    def reset(self):
        """Input: none. Output: clear captured faces and resume acquisition."""
        with self.lock:
            self.faces.clear()
            self.hsv_faces.clear()
            self.revision += 1
            self.current = ()
            self.current_hsv = None
            self._clear_hold()
            self.enabled = True
            self.message = "Show a face and hold still"

    def forget(self, center):
        """Input: center color. Output: remove that face for another acquisition."""
        with self.lock:
            self.faces.pop(center, None)
            self.hsv_faces.pop(center, None)
            self.revision += 1
            self._clear_hold()


scanner = FaceScanner()
