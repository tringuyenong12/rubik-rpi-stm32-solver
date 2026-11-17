"""Adjustable camera ROI, stored as fractions so it survives resolution changes."""

import json
from pathlib import Path

import cv2
import numpy as np

FACE_SIZE = 360
FACE_MARGIN = 32  # About 9% extra space on each side; keep the calibrated square.


def expanded_corners(corners):
    """Project a small border around the face without moving its calibrated grid."""
    edge = FACE_SIZE - 1
    source = np.float32(corners)
    target = np.float32([[0, 0], [edge, 0], [edge, edge], [0, edge]])
    inverse = cv2.getPerspectiveTransform(target, source)
    margin = FACE_MARGIN
    outer = np.float32([[[-margin, -margin], [edge+margin, -margin],
                         [edge+margin, edge+margin], [-margin, edge+margin]]])
    return cv2.perspectiveTransform(outer, inverse)[0]


class CameraROI:
    def __init__(self, path=None):
        self.path = path or Path(__file__).resolve().parents[3] / 'calibration' / 'camera_roi.json'
        self.region = None
        self.corners = None
        self.picking = None
        self.shape = None
        self.start = None
        self.end = None
        self.message = ''
        self._shade_key = None
        self._shade_mask = None
        self._shade_polygon = None
        self._shade_lut = np.arange(256, dtype=np.uint8) // 3

    def load(self, camera_id):
        self.camera_id = str(camera_id)
        self.message = ''
        self.region = None
        self.corners = None
        self.picking = None
        self.start = self.end = None
        try:
            values = json.loads(self.path.read_text(encoding='utf-8')).get(self.camera_id)
            if isinstance(values, dict):
                corners = np.asarray(values.get('corners', []), dtype=np.float32)
                if (corners.shape == (4, 2) and np.all(np.isfinite(corners))
                        and np.all((corners >= 0) & (corners <= 1))
                        and cv2.isContourConvex(corners) and cv2.contourArea(corners) > .001):
                    self.corners = tuple(tuple(float(v) for v in point) for point in corners)
                values = values.get('rectangle')
            if (isinstance(values, list) and len(values) == 4
                    and all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in values)
                    and values[0] < values[2] and values[1] < values[3]):
                self.region = tuple(values)
        except (OSError, ValueError, AttributeError):
            pass

    def bounds(self, shape):
        self.shape = shape[:2]
        h, w = self.shape
        if self.region is None:
            side = max(1, round(min(h, w) * .8))
            x, y = (w - side) // 2, (h - side) // 2
            return x, y, x + side, y + side
        x1, y1, x2, y2 = self.region
        x1, y1 = min(w - 1, round(x1 * w)), min(h - 1, round(y1 * h))
        return x1, y1, max(x1 + 1, round(x2 * w)), max(y1 + 1, round(y2 * h))

    def save(self):
        try:
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if not isinstance(data, dict):
                    data = {}
            except (OSError, ValueError):
                data = {}
            data[self.camera_id] = ({'rectangle': self.region, 'corners': self.corners}
                                    if self.corners is not None else self.region)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=2), encoding='utf-8')
            self.message = 'ROI saved'
        except OSError:
            self.message = 'ROI active; could not save settings'

    def mouse(self, event, x, y, flags, param):
        if self.shape is None:
            return
        h, w = self.shape
        point = (max(0, min(x, w - 1)), max(0, min(y, h - 1)))
        if self.picking is not None:
            if event == cv2.EVENT_LBUTTONDOWN:
                self.picking.append((point[0] / w, point[1] / h))
                if len(self.picking) == 4:
                    corners = np.asarray(self.picking, dtype=np.float32)
                    if cv2.isContourConvex(corners) and cv2.contourArea(corners) > .01:
                        self.corners = tuple(self.picking)
                        self.save()
                    else:
                        self.message = 'Invalid corners: press P to retry'
                    self.picking = None
            return
        if event == cv2.EVENT_LBUTTONDOWN:
            self.start = self.end = point
        elif event == cv2.EVENT_MOUSEMOVE and self.start is not None:
            self.end = point
        elif event == cv2.EVENT_LBUTTONUP and self.start is not None:
            x1, x2 = sorted((self.start[0], point[0]))
            y1, y2 = sorted((self.start[1], point[1]))
            if min(x2 - x1, y2 - y1) >= 60:
                self.region = (x1 / w, y1 / h, x2 / w, y2 / h)
                self.corners = None
                self.save()
            else:
                self.message = 'ROI too small (minimum 60 x 60)'
            self.start = self.end = None

    def selection(self, shape):
        self.bounds(shape)
        if self.corners is not None:
            h, w = shape[:2]
            return tuple((x * w, y * h) for x, y in self.corners)
        return self.bounds(shape)

    def draw(self, frame):
        x1, y1, x2, y2 = self.bounds(frame.shape)
        # Dim only the preview; detection always receives the original pixels.
        if self.corners is not None:
            key = (frame.shape[:2], self.corners)
            if key != self._shade_key:
                self._shade_polygon = np.rint(expanded_corners(self.selection(frame.shape))).astype(np.int32)
                self._shade_mask = np.full(frame.shape[:2], 255, dtype=np.uint8)
                cv2.fillConvexPoly(self._shade_mask, self._shade_polygon, 0)
                self._shade_key = key
            polygon = self._shade_polygon
            # Native masked copying avoids slow, allocating NumPy boolean indexing.
            cv2.copyTo(cv2.LUT(frame, self._shade_lut), self._shade_mask, frame)
            cv2.polylines(frame, [polygon], True, (0, 230, 255), 2)
        else:
            frame[:y1] //= 3
            frame[y2:] //= 3
            frame[y1:y2, :x1] //= 3
            frame[y1:y2, x2:] //= 3
            cv2.rectangle(frame, (x1, y1), (x2 - 1, y2 - 1), (0, 230, 255), 2)
        if self.start is not None:
            cv2.rectangle(frame, self.start, self.end, (255, 255, 255), 1)
        if self.picking is not None:
            for point in self.picking:
                cv2.circle(frame, (round(point[0]*frame.shape[1]), round(point[1]*frame.shape[0])),
                           5, (255, 255, 255), -1)
            text = f'Click corner {len(self.picking)+1}/4: TL, TR, BR, BL of face'
        else:
            text = (self.message if self.message and self.message != 'ROI saved'
                    else 'ROI: drag | P: 4 corners | R: reset')
        cv2.putText(frame, text, (8, frame.shape[0] - 33),
                    cv2.FONT_HERSHEY_SIMPLEX, .43, (0, 230, 255), 1, cv2.LINE_AA)
        return frame
