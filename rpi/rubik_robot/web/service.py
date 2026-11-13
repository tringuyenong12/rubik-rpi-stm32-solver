"""Application workflows; hardware movement remains an external UART contract."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from rubik_robot.cube.state import FACE_ORDER
from rubik_robot.web.camera import Camera
from rubik_robot.web.cube import scramble_for, solution_for, validated_cube
from rubik_robot.web.camera_tutorial import CameraTutorial
from rubik_robot.web.scan import assemble_faces, camera_face, canonical_face, fixed_route
from rubik_robot.web.vision import COLORS


class Service:
    """Coordinate scanning, verified tutorials, scramble generation and calibration."""

    def __init__(self, camera: Camera, calibration_path: Path):
        """Input: camera and profile path. Output: idle application with saved calibration."""
        self.camera = camera
        self.path = calibration_path
        self.lock = threading.RLock()
        self.faces: dict = {}
        self.tutorial = CameraTutorial()
        self.scan: dict | None = None
        self.last_scramble: dict | None = None
        self.last_solution: dict | None = None
        self.after_seq = 0
        self.ready_at = 0.0
        self.calibration_error = ""
        if self.path.exists():
            try:
                saved = json.loads(self.path.read_text(encoding="utf-8"))
                for color, lab in saved.items():
                    if color not in COLORS.values() or not isinstance(lab, list) or len(lab) != 3:
                        raise ValueError("Sai cấu trúc profile.")
                    if any(not isinstance(v, (int, float)) or not 0 <= v <= 255 for v in lab):
                        raise ValueError("Mẫu LAB ngoài miền.")
                self.camera.profile = saved
            except (ValueError, OSError, AttributeError) as exc:
                self.calibration_error = str(exc)

    def calibrate(self, face: str) -> dict:
        """Input: known face name. Output: stored median center LAB sample."""
        self.require_idle_scan()
        self.require_idle_tutorial()
        if face not in FACE_ORDER or len(face) != 1:
            raise ValueError("Chọn mặt U/R/F/D/L/B để lấy mẫu tâm.")
        sample = self.camera.snapshot()
        if not sample.get("lab") or time.monotonic() - sample.get("timestamp", 0) > 2:
            raise ValueError("Chưa có ảnh mới; mở camera và đặt tâm sticker vào ô giữa.")
        with self.camera.lock:
            self.camera.profile[COLORS[face]] = sample["lab"][4]
            profile = dict(self.camera.profile)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return {"calibration": profile, "saved": str(self.path)}

    def clear(self) -> dict:
        """Input: none. Output: empty face collection and stopped workflows."""
        self.tutorial.stop()
        self.tutorial = CameraTutorial()
        self.faces, self.scan, self.last_solution = {}, None, None
        return {"ok": True}

    def require_idle_scan(self) -> None:
        """Input: current scan. Output: error if a workflow would overwrite an active scan."""
        if self.scan and self.scan["status"] not in {"complete", "cancelled", "error"}:
            raise ValueError("Huỷ hoặc hoàn tất lượt quét trước khi thực hiện thao tác này.")

    def require_idle_tutorial(self) -> None:
        """Input: tutorial lifetime. Output: error while it owns the camera."""
        if self.tutorial.snapshot()["running"]:
            raise ValueError("Dừng hướng dẫn camera trước khi dùng camera cho chức năng khác.")

    def start_tutorial(self, index: int, backend: str) -> dict:
        """Input: camera settings. Output: complete two-file tutorial started at front-face scan."""
        self.require_idle_scan()
        self.require_idle_tutorial()
        self.camera.stop()
        self.faces, self.last_solution = {}, None
        self.tutorial.start(index, backend)
        return self.tutorial.snapshot()

    def current_sample(self) -> dict:
        """Input: none. Output: recent stable face, or error without recording it."""
        sample = self.camera.snapshot()
        if sample.get("stable", 0) < 8 or time.monotonic() - sample.get("timestamp", 0) > 2:
            raise ValueError("Giữ mặt trong khung đến khi ổn định 8 khung hình và đủ độ tin cậy.")
        return sample

    def capture(self, face: str, colors: list | None = None) -> dict:
        """Input: canonical face and optional manual colors. Output: saved nine stickers."""
        self.require_idle_tutorial()
        if face not in FACE_ORDER or len(face) != 1:
            raise ValueError("Tên mặt không hợp lệ.")
        if self.scan and self.scan["status"] not in {"complete", "cancelled", "error"}:
            raise ValueError("Dừng lượt quét tự động trước khi sửa các mặt.")
        values = colors if colors is not None else self.current_sample()["colors"]
        if not isinstance(values, list) or len(values) != 9 or any(v not in COLORS.values() for v in values):
            raise ValueError("Mặt phải có chín màu hợp lệ.")
        if any(f != face and values[4] == grid[4] for f, grid in self.faces.items()):
            raise ValueError("Màu tâm này đã thuộc mặt khác; không ghi đè nhầm mặt.")
        self.faces[face] = values[:]
        self.last_solution = None
        return {"faces": self.faces}

    def solve(self, state: str | None = None, tutorial: bool = False) -> dict:
        """Input: state or six captured faces. Output: verified solution; tutorial has its own flow."""
        self.require_idle_scan()
        if tutorial:
            raise ValueError("Chức năng 1 bắt đầu bằng /api/tutorial/start và tự quét sáu mặt.")
        self.require_idle_tutorial()
        self.tutorial = CameraTutorial()
        state = state if state is not None else assemble_faces(self.faces)
        result = solution_for(state)
        self.last_solution = result
        return result

    def scramble(self, level: str, seed: int | None = None) -> dict:
        """Input: level and seed. Output: saved generated task; sends no UART."""
        self.last_scramble = scramble_for(level, seed)
        return self.last_scramble

    def start_scan(self, mode: str, demo_state: str | None = None) -> dict:
        """Input: manual/external/demo mode. Output: scan route waiting for stable capture."""
        self.require_idle_scan()
        self.require_idle_tutorial()
        if mode not in {"manual", "external", "demo"}:
            raise ValueError("Chế độ quét không hợp lệ.")
        if mode == "demo":
            if demo_state is None:
                demo_state = scramble_for("easy", 17)["state"]
            validated_cube(demo_state)
        elif len(self.camera.profile) != 6:
            raise ValueError("Quét tự động cần hiệu chỉnh đủ sáu mẫu tâm trước.")
        self.tutorial = CameraTutorial()
        self.faces, self.last_solution = {}, None
        self.scan = {"mode": mode, "route": fixed_route(), "index": 0,
                     "status": "capturing", "faces": {}, "error": "",
                     "demo_state": demo_state if mode == "demo" else None}
        self._settle()
        return self.scan_public()

    def _settle(self) -> None:
        """Input: none. Output: discard old frames and allow one second of settling."""
        self.after_seq = self.camera.snapshot()["seq"] + 8
        self.ready_at = time.monotonic() + 1.0

    def scan_public(self) -> dict | None:
        """Input: internal scan. Output: public progress and next command, without demo state."""
        if not self.scan:
            return None
        public = {k: v for k, v in self.scan.items() if k != "demo_state"}
        public["next"] = self.scan["route"][self.scan["index"]] if self.scan["index"] < len(self.scan["route"]) else None
        return public

    def acknowledge(self, command_id: int, result: str) -> dict:
        """Input: exact pending ID and DONE. Output: next scan stage; rejects stale ACK."""
        if not self.scan or self.scan["status"] != "waiting_done":
            raise ValueError("Không có lệnh đổi tư thế đang chờ DONE.")
        step = self.scan["route"][self.scan["index"]]
        if command_id != step["id"] or result != "DONE":
            raise ValueError("Cần DONE đúng ID lệnh hiện tại; OK không xác nhận chuyển động hoàn tất.")
        self.scan["index"] += 1
        self._settle()
        self._advance_scan()
        return self.scan_public()

    def _advance_scan(self) -> None:
        """Input: current route index. Output: next pending stage or verified final solution."""
        if self.scan["index"] == len(self.scan["route"]):
            try:
                state = assemble_faces(self.scan["faces"])
                self.last_solution = solution_for(state)
                self.scan["solution"] = self.last_solution
                self.scan["status"] = "complete"
                self.faces = dict(self.scan["faces"])
            except (ValueError, RuntimeError, OSError) as exc:
                self.scan["status"], self.scan["error"] = "error", str(exc)
            return
        step = self.scan["route"][self.scan["index"]]
        self.scan["status"] = "capturing" if step["kind"] == "capture" else "waiting_done"

    def _record_scan(self, raw: list[str]) -> None:
        """Input: reliable camera grid. Output: orientation-correct face and next stage."""
        step = self.scan["route"][self.scan["index"]]
        values = canonical_face(raw, step["face"], step["orientation"])
        centers = [v[4] for v in self.scan["faces"].values()]
        if values[4] in centers:
            self.scan["error"] = "Tâm trùng mặt trước: kiểm tra lệnh đổi tư thế; chưa chụp mặt này."
            return
        self.scan["error"] = ""
        self.scan["faces"][step["face"]] = values
        self.scan["index"] += 1
        self._advance_scan()

    def demo_step(self) -> dict:
        """Input: demo scan only. Output: one simulated ACK/capture; no camera or hardware I/O."""
        if not self.scan or self.scan["mode"] != "demo":
            raise ValueError("Chỉ dùng bước giả lập trong chế độ demo.")
        if self.scan["status"] == "waiting_done":
            step = self.scan["route"][self.scan["index"]]
            return self.acknowledge(step["id"], "DONE")
        if self.scan["status"] == "capturing":
            step = self.scan["route"][self.scan["index"]]
            offset = FACE_ORDER.index(step["face"]) * 9
            canonical = [COLORS[f] for f in self.scan["demo_state"][offset:offset + 9]]
            self._record_scan(camera_face(canonical, step["face"], step["orientation"]))
        return self.scan_public()

    def tick(self) -> None:
        """Input: latest camera sample. Output: progress only after fresh, stable observations."""
        sample = self.camera.snapshot()
        if sample.get("seq", 0) < self.after_seq or time.monotonic() < self.ready_at:
            return
        if sample.get("stable", 0) < 8 or time.monotonic() - sample.get("timestamp", 0) > 2:
            return
        if self.scan and self.scan["mode"] != "demo" and self.scan["status"] == "capturing":
            self._record_scan(sample["colors"])

    def status(self) -> dict:
        """Input: none. Output: live public camera/workflow state after safe progress tick."""
        with self.lock:
            self.tick()
            tutorial = self.tutorial.snapshot()
            if tutorial["solution"] is not None:
                self.last_solution = tutorial["solution"]
            return {"camera": self.camera.snapshot(), "faces": self.faces, "tutorial": tutorial,
                    "scan": self.scan_public(), "solution": self.last_solution,
                    "calibration_error": self.calibration_error}
