"""One shared camera worker, with Windows DirectShow support and explicit lifetime."""

from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from rubik_robot.web.vision import StableFace, sample_face


class Camera:
    """Own capture, calibration and last analyzed frame; never opens at import."""

    def __init__(self, index: int = 1, backend: str = "dshow"):
        """Input: camera index/backend. Output: stopped camera service."""
        self.index, self.backend = index, backend
        self.corners = [[0.28, 0.2], [0.72, 0.2], [0.72, 0.8], [0.28, 0.8]]
        self.profile: dict = {}
        self.mode = "grid"
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.sample = {"colors": [], "confidence": [], "stable": 0, "seq": 0}
        self.jpeg = b""
        self.error = "Camera chưa mở."

    def start(self, index: int, backend: str) -> None:
        """Input: camera configuration. Output: running worker or ValueError."""
        if not 0 <= index <= 10 or backend not in {"auto", "dshow", "msmf", "v4l2"}:
            raise ValueError("Camera ID phải 0..10; backend không hợp lệ.")
        self.stop()
        self.index, self.backend = index, backend
        self.error = "Đang mở camera…"
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name="rubik-camera")
        self.thread.start()

    def stop(self) -> None:
        """Input: none. Output: worker stopped and camera released."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=4)
            if self.thread.is_alive():
                raise ValueError("Driver camera chưa dừng; chờ rồi thử lại.")
        self.thread = None
        with self.lock:
            self.sample = {"colors": [], "confidence": [], "stable": 0, "seq": self.sample["seq"] + 1}
            self.jpeg = b""
            self.error = "Camera đã dừng."

    def snapshot(self) -> dict:
        """Input: none. Output: copy of latest colors, confidence and device state."""
        with self.lock:
            return {**self.sample, "error": self.error, "index": self.index,
                    "backend": self.backend, "corners": self.sample.get("detected_corners") or self.corners,
                    "calibration": list(self.profile), "mode": self.mode,
                    "running": bool(self.thread and self.thread.is_alive())}

    def configure(self, corners: list | None = None, mode: str | None = None) -> None:
        """Input: optional ROI and detector. Output: updated validated camera settings."""
        if corners is not None:
            points = np.asarray(corners, dtype=float)
            if points.shape != (4, 2) or not np.isfinite(points).all() or np.any(points < 0) or np.any(points > 1):
                raise ValueError("Cần bốn điểm trong ảnh, thứ tự TL/TR/BR/BL.")
            if not cv2.isContourConvex((points * 1000).astype(np.int32)):
                raise ValueError("Bốn điểm phải tạo tứ giác lồi, không tự cắt.")
        if mode is not None and mode not in {"grid", "contour"}:
            raise ValueError("Detector không hợp lệ.")
        with self.lock:
            if corners is not None:
                self.corners = corners
            if mode is not None:
                self.mode = mode

    def _run(self) -> None:
        """Input: stored settings. Output: analyzed JPEG frames until stop/error."""
        backends = {"auto": cv2.CAP_ANY, "dshow": cv2.CAP_DSHOW,
                    "msmf": cv2.CAP_MSMF, "v4l2": cv2.CAP_V4L2}
        cap = cv2.VideoCapture(self.index, backends[self.backend])
        stable = StableFace()
        try:
            if not cap.isOpened():
                raise ValueError(f"Không mở được camera {self.index}. Đóng ứng dụng khác hoặc đổi ID/backend.")
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            failures = 0
            while not self.stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    failures += 1
                    if failures > 20:
                        raise ValueError("Camera mất hình; kiểm tra cáp USB và quyền camera.")
                    self.stop_event.wait(0.1)
                    continue
                failures = 0
                with self.lock:
                    corners, profile, mode = list(self.corners), dict(self.profile), self.mode
                sample = sample_face(frame, corners, profile, mode)
                sample["stable"] = stable.update(sample)
                sample["timestamp"] = time.monotonic()
                encoded, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
                with self.lock:
                    sample["seq"] = self.sample["seq"] + 1
                    self.sample = sample
                    self.jpeg = jpeg.tobytes() if encoded else b""
                    self.error = ""
                self.stop_event.wait(0.07)
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                self.sample["stable"] = 0
        finally:
            cap.release()
