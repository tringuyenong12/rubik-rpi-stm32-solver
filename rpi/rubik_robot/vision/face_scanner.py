"""Collect stable camera faces by center color for the desktop client."""

from collections import Counter, deque
from threading import Lock
from time import monotonic
import numpy as np


COLORS = ("yellow", "green", "red", "white", "blue", "orange")


class FaceScanner:
    """Input: successive 3x3 color grids. Output: six center-keyed faces."""

    def __init__(self, stable_seconds=0.18, min_samples=4, require_transition=False):
        """Input: hold duration and frame count. Output: an empty scan session."""
        self.stable_seconds = stable_seconds
        self.min_samples = min_samples
        self.require_transition = require_transition
        self.last_captured = ()
        self.transition_ready = True
        self.missing_since = None
        self.lock = Lock()
        self.enabled = True
        self.faces = {}
        self.hsv_faces = {}
        self.hsv_observations = deque(maxlen=max(7, min_samples))
        self.revision = 0
        self.current = ()
        self.current_hsv = None
        self.current_confirmed = False
        self.pending = ()
        self.started = 0.0
        self.samples = 0
        self.observations = deque(maxlen=max(7, min_samples))
        self.last_valid = 0.0
        self.progress = 0
        self.message = "Show a face and hold still"

    def update(self, grid, now=None, hsv_grid=None, displayed_grid=None):
        """Input: detected grid and optional clock. Output: update session state."""
        now = monotonic() if now is None else now
        valid = len(grid) == 3 and all(len(row) == 3 for row in grid)
        face = tuple(color for row in grid for color in row) if valid else ()
        if any(color not in COLORS for color in face):
            face = ()
        numeric = np.asarray(hsv_grid, dtype=float) if hsv_grid is not None else np.asarray([])
        sample = numeric.reshape(9, 3) if numeric.shape == (3, 3, 3) and np.all(np.isfinite(numeric)) else None
        shown = (tuple(color for row in displayed_grid for color in row)
                 if displayed_grid is not None and len(displayed_grid) == 3
                 and all(len(row) == 3 for row in displayed_grid) else ())
        with self.lock:
            self.current = face
            self.current_hsv = sample if face else None
            self.current_confirmed = bool(face) and (displayed_grid is None or shown == face)
            if not face:
                if self.missing_since is None:
                    self.missing_since = now
                if now - self.missing_since >= .35:
                    self.transition_ready = True
                if now - self.last_valid > 0.25:
                    self._clear_hold()
                self.message = "Looking for all 9 stickers"
                return
            self.missing_since = None
            if not self.enabled:
                self.message = "Auto scan paused"
                return
            center = face[4]
            if self.require_transition:
                # A center-label flicker cannot turn the same eight stickers
                # into a different physical face, even after a long pause.
                for saved_center, saved in self.faces.items():
                    differences = sum(a != b for i, (a, b) in enumerate(zip(face, saved)) if i != 4)
                    if center != saved_center and differences <= 1:
                        self._clear_hold()
                        self.message = f'Center uncertain: still looks like {saved_center}'
                        return
                if self.last_captured and not self.transition_ready:
                    changes = sum(a != b for i, (a, b) in enumerate(zip(face, self.last_captured)) if i != 4)
                    if changes >= 3:
                        self.transition_ready = True
                    else:
                        self._clear_hold()
                        self.message = 'Saved - turn to a different face before scanning again'
                        return
            if center in self.faces:
                self._clear_hold()
                self.message = f"{center}: already saved - show another face"
                if len(self.faces) == 6:
                    self.message = self._count_summary()
                return
            if not self.pending or center != self.pending[4]:
                self._clear_hold()
                self.pending, self.started, self.samples = face, now, 0
            elif self.require_transition and sum(a != b for a, b in zip(face, self.pending)) >= 2:
                self._clear_hold()
                self.pending, self.started = face, now
            elif (self.require_transition and face != self.pending and len(self.observations) >= 2
                  and self.observations[-1] == face and self.observations[-2] == face):
                # A persistent one-sticker change needs a fresh full hold too.
                self._clear_hold()
                self.pending, self.started = face, now
            if self.require_transition and sample is not None and self.hsv_observations:
                previous = self.hsv_observations[-1]
                if previous is not None:
                    hue_change = abs((sample[4, 0] - previous[4, 0] + 90) % 180 - 90)
                    sv_change = np.abs(sample[4, 1:] - previous[4, 1:])
                    if ((min(sample[4, 1], previous[4, 1]) > 35 and hue_change > 5)
                            or sv_change[0] > 18 or sv_change[1] > 25):
                        self._clear_hold()
                        self.pending, self.started = face, now
            self.last_valid = now
            self.observations.append(face)
            self.hsv_observations.append(sample)
            self.samples = len(self.observations)
            self.progress = min(99, int(100 * self.samples / self.min_samples))
            if self.stable_seconds > 0:
                self.progress = min(self.progress, int(100 * max(0, now - self.started) / self.stable_seconds))
            self.message = f"Hold {center} still"
            if self.samples < self.min_samples or now - self.started < self.stable_seconds:
                return
            votes = [Counter(column).most_common(1)[0] for column in zip(*self.observations)]
            if any(count / self.samples < 0.8 for _, count in votes):
                self.message = f"Checking {center} colors"
                return
            voted_face = tuple(color for color, _ in votes)
            if displayed_grid is not None and (not self.current_confirmed or voted_face != face):
                self.message = f'Checking {center}: saved colors must match the current display'
                return
            samples = [sample for sample in self.hsv_observations if sample is not None]
            numeric_face = self._median_hsv(samples)
            if self._save_face(voted_face, numeric_face):
                self.last_captured = voted_face
                self.transition_ready = False
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
            if not self.current or not self.current_confirmed:
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
            self.current_confirmed = False
            self.last_captured = ()
            self.transition_ready = True
            self.missing_since = None
            self._clear_hold()
            self.enabled = True
            self.message = "Show a face and hold still"

    def forget(self, center):
        """Input: center color. Output: remove that face for another acquisition."""
        with self.lock:
            self.faces.pop(center, None)
            self.hsv_faces.pop(center, None)
            if self.last_captured and self.last_captured[4] == center:
                self.last_captured = ()
                self.transition_ready = True
            self.revision += 1
            self._clear_hold()


def new_camera_scanner():
    """Use a longer hold for camera startup and orange/red settling."""
    return FaceScanner(stable_seconds=1.5, min_samples=12, require_transition=True)


scanner = new_camera_scanner()
