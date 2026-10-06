from __future__ import annotations

from pathlib import Path

import cv2


class CameraCapture:
    def __init__(self, camera_id: int = 0, width: int = 1280, height: int = 720) -> None:
        self.camera_id = camera_id
        self.width = width
        self.height = height

    def capture(self, output_path: Path | None = None):
        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open camera id {self.camera_id}")

        try:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Failed to capture frame")
            if output_path is not None:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(output_path), frame)
            return frame
        finally:
            cap.release()

