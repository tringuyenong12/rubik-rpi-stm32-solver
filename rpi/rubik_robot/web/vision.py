"""Sticker detection, BGR/LAB color classification and stable-frame filtering."""

from __future__ import annotations

from collections import deque

import cv2
import numpy as np

COLORS = {"U": "white", "R": "red", "F": "green", "D": "yellow", "L": "orange", "B": "blue"}
RGB = {"white": "#f4f5f7", "red": "#ee5261", "green": "#29bf91",
       "yellow": "#f6ce50", "orange": "#ff943e", "blue": "#4387ec", "unknown": "#68778c"}


def classify_bgr_color(bgr: np.ndarray) -> str:
    """Input: BGR sample. Output: one of six color labels or unknown."""
    b, g, r = [float(v) for v in bgr]
    if b > 120 and g > 120 and r > 100:
        return "white"
    if b < 100 and g > 120 and r > 120 and abs(g - r) < 30:
        return "yellow"
    if b > g > r:
        return "blue"
    if g > b and g > r and abs(b - r) < 30:
        return "green"
    if r > b and r > g and abs(b - g) < 30 and b < 80:
        return "red"
    if g < r and b < g and r > 120:
        return "orange"
    return "unknown"


def detect_sticker_contours(frame: np.ndarray) -> list[list[int]]:
    """Input: BGR frame. Output: nine sticker boxes ordered by row and column."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    mask = cv2.adaptiveThreshold(gray, 20, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 5, 0)
    contours = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)[-2]
    scale = frame.shape[0] * frame.shape[1] / (640 * 480)
    boxes = []
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if 1000 * scale < area < 3000 * scale and abs((perimeter / 4) ** 2 - area) < 150 * scale:
            box = list(cv2.boundingRect(contour))
            if all(np.linalg.norm(np.array(box[:2]) - np.array(other[:2])) > 8 for other in boxes):
                boxes.append(box)
    if len(boxes) != 9:
        return []
    ordered = sorted(boxes, key=lambda box: box[1] + box[3] / 2)
    return [box for row in range(3) for box in sorted(ordered[row * 3:row * 3 + 3], key=lambda box: box[0])]


def sample_face(frame: np.ndarray, corners: list, profile: dict, mode: str = "grid") -> dict:
    """Input: BGR frame, normalized TL/TR/BR/BL ROI, LAB centers. Output: nine colors/confidences."""
    height, width = frame.shape[:2]
    points = np.asarray(corners, dtype=np.float32) * [width, height]
    if points.shape != (4, 2) or not np.isfinite(points).all() or cv2.contourArea(points.astype(np.float32)) < 400:
        raise ValueError("Vùng quét phải là tứ giác đủ lớn theo thứ tự TL/TR/BR/BL.")
    transform = cv2.getPerspectiveTransform(points.astype(np.float32), np.float32([[0, 0], [299, 0], [299, 299], [0, 299]]))
    warped = cv2.warpPerspective(frame, transform, (300, 300))
    gray_inner = cv2.cvtColor(warped[8:-8, 8:-8], cv2.COLOR_BGR2GRAY)
    sharpness = float(cv2.Laplacian(gray_inner, cv2.CV_64F).var())
    boxes = detect_sticker_contours(frame) if mode == "contour" else []
    if mode == "contour" and len(boxes) != 9:
        return {"colors": [], "confidence": [], "lab": [], "ready": False, "reason": "Chưa tìm đủ 9 ô bằng đường bao; thử chế độ khung cố định."}
    colors, confidence, labs = [], [], []
    calibrated = len(profile) == 6
    for i in range(9):
        if boxes:
            x, y, w, h = boxes[i]
            patch = frame[y + h // 4:y + 3 * h // 4, x + w // 4:x + 3 * w // 4]
        else:
            row, col = divmod(i, 3)
            patch = warped[row * 100 + 25:row * 100 + 75, col * 100 + 25:col * 100 + 75]
        lab_pixels = cv2.cvtColor(patch, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(float)
        lab = np.median(lab_pixels, axis=0)
        labs.append(lab.tolist())
        if calibrated:
            distances = sorted((float(np.linalg.norm(lab - np.asarray(center))), color) for color, center in profile.items())
            first, second = distances[:2]
            certainty = max(0.0, min(1.0, (second[0] - first[0]) / max(second[0], 1.0)))
            certainty *= max(0.0, 1 - first[0] / 90)
            colors.append(first[1] if first[0] < 70 else "unknown")
            confidence.append(round(certainty, 3))
        else:
            colors.append(classify_bgr_color(np.median(patch.reshape(-1, 3), axis=0)))
            confidence.append(0.55 if colors[-1] != "unknown" else 0.0)
    return {"colors": colors, "confidence": confidence, "lab": labs, "sharpness": round(sharpness, 1),
            "ready": "unknown" not in colors and min(confidence) >= (0.22 if calibrated else 0.5) and sharpness >= 15,
            "calibrated": calibrated,
            "detected_corners": [[boxes[0][0] / width, boxes[0][1] / height],
                                 [(boxes[2][0] + boxes[2][2]) / width, boxes[2][1] / height],
                                 [(boxes[8][0] + boxes[8][2]) / width, (boxes[8][1] + boxes[8][3]) / height],
                                 [boxes[6][0] / width, (boxes[6][1] + boxes[6][3]) / height]] if boxes else None,
            "reason": "Ảnh mờ hoặc khung chưa ôm mặt Rubik." if sharpness < 15 else "" if calibrated else "Chưa đủ 6 mẫu tâm: đang dùng ngưỡng màu BGR."}


class StableFace:
    """Consecutive-frame acceptance gate; rejects blur, uncertainty and motion."""

    def __init__(self, frames: int = 8):
        """Input: required consecutive frames. Output: empty stability window."""
        self.history = deque(maxlen=frames)

    def update(self, sample: dict) -> int:
        """Input: analysis sample. Output: number of consecutive reliable equal grids."""
        signature = tuple(sample.get("colors", []))
        if not sample.get("ready") or not signature:
            self.history.clear()
            return 0
        if self.history and signature != self.history[-1]:
            self.history.clear()
        self.history.append(signature)
        return len(self.history)
