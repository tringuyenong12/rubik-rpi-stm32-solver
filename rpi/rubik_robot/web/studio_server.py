"""Local HTTP API and static UI; uses the existing Python dependencies only."""

from __future__ import annotations

import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from rubik_robot.web.camera import Camera
from rubik_robot.web.scan import fixed_route
from rubik_robot.web.service import Service

STATIC = Path(__file__).with_name("static") / "studio"
ROOT = Path(__file__).resolve().parents[3]


def make_handler(service: Service) -> type[BaseHTTPRequestHandler]:
    """Input: application service. Output: request handler bound to its state."""

    class Handler(BaseHTTPRequestHandler):
        """Serve the localhost app and bounded JSON requests."""

        def log_message(self, format: str, *args) -> None:
            """Input: HTTP log format. Output: suppress repetitive frame polling logs."""

        def respond(self, data: bytes, content_type: str, status: int = 200) -> None:
            """Input: bytes/type/status. Output: complete HTTP response."""
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def json_response(self, payload: dict, status: int = 200) -> None:
            """Input: JSON-compatible object/status. Output: UTF-8 JSON response."""
            self.respond(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode(), "application/json; charset=utf-8", status)

        def do_GET(self) -> None:
            """Input: URL. Output: static asset, live frame or workflow JSON."""
            path = urlsplit(self.path).path
            try:
                if path == "/api/status":
                    self.json_response(service.status())
                elif path == "/api/scan":
                    service.status()
                    self.json_response({"scan": service.scan_public(), "route": fixed_route()})
                elif path in {"/api/frame.jpg", "/api/tutorial/frame.jpg"}:
                    camera_owner = service.tutorial if path == "/api/tutorial/frame.jpg" else service.camera
                    with camera_owner.lock:
                        frame = camera_owner.jpeg
                    if frame:
                        self.respond(frame, "image/jpeg")
                    else:
                        self.respond(b"No frame", "text/plain", 503)
                else:
                    name = "index.html" if path == "/" else path.lstrip("/")
                    if name not in {"index.html", "app.js", "styles.css"}:
                        self.json_response({"error": "Không tìm thấy."}, 404)
                        return
                    self.respond((STATIC / name).read_bytes(), mimetypes.guess_type(name)[0] or "application/octet-stream")
            except ValueError as exc:
                self.json_response({"error": str(exc)}, 400)

        def do_POST(self) -> None:
            """Input: JSON API action. Output: result or explicit validation error."""
            try:
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("API yêu cầu Content-Type: application/json.")
                origin = self.headers.get("Origin")
                port = self.server.server_address[1]
                if origin and origin not in {f"http://127.0.0.1:{port}", f"http://localhost:{port}"}:
                    raise ValueError("Chỉ nhận thao tác từ trang localhost của ứng dụng.")
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 65536:
                    raise ValueError("JSON body phải từ 1 đến 65536 byte.")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("JSON phải là object.")
                with service.lock:
                    result = self.dispatch(urlsplit(self.path).path, body)
                self.json_response(result)
            except (ValueError, TypeError, KeyError) as exc:
                self.json_response({"error": str(exc)}, 400)
            except Exception as exc:
                self.json_response({"error": f"Không hoàn tất thao tác: {exc}"}, 500)

        def dispatch(self, path: str, body: dict) -> dict:
            """Input: path and validated JSON object. Output: corresponding service action."""
            if path == "/api/camera/start":
                service.require_idle_scan()
                service.require_idle_tutorial()
                service.camera.start(int(body.get("index", 1)), body.get("backend", "dshow"))
                return {"ok": True}
            if path == "/api/camera/stop":
                service.require_idle_tutorial()
                service.camera.stop()
                return {"ok": True}
            if path == "/api/camera/config":
                service.require_idle_scan()
                service.require_idle_tutorial()
                service.camera.configure(body.get("corners"), body.get("mode"))
                return {"ok": True}
            if path == "/api/calibrate":
                return service.calibrate(body["face"])
            if path == "/api/faces/capture":
                return service.capture(body["face"], body.get("colors"))
            if path == "/api/clear":
                return service.clear()
            if path == "/api/solve":
                return service.solve(body.get("state"), bool(body.get("tutorial", False)))
            if path == "/api/scramble":
                return service.scramble(body.get("level", "easy"), body.get("seed"))
            if path == "/api/tutorial/start":
                return service.start_tutorial(int(body.get("index", service.camera.index)), body.get("backend", service.camera.backend))
            if path == "/api/tutorial/stop":
                service.tutorial.stop()
                return {"ok": True}
            if path == "/api/scan/start":
                return service.start_scan(body.get("mode", "manual"), body.get("state"))
            if path == "/api/scan/ack":
                return service.acknowledge(int(body["id"]), body.get("result", ""))
            if path == "/api/scan/demo-step":
                return service.demo_step()
            if path == "/api/scan/cancel":
                if service.scan:
                    service.scan["status"] = "cancelled"
                return {"ok": True, "note": "Huỷ phần mềm; không tự di chuyển khối về gốc."}
            raise ValueError("API không tồn tại.")

    return Handler


def main() -> None:
    """Input: CLI host/port/camera flags. Output: local web server until Ctrl+C."""
    parser = argparse.ArgumentParser(description="Rubik Studio — local camera web app")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--camera", type=int, default=1)
    parser.add_argument("--backend", choices=["auto", "dshow", "msmf", "v4l2"], default="dshow")
    args = parser.parse_args()
    camera = Camera(args.camera, args.backend)
    service = Service(camera, ROOT / "calibration" / "web_color_profile.json")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(service))
    print(f"Rubik Studio: http://127.0.0.1:{args.port}", flush=True)
    print("Camera opens only when you click Mo camera. Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        service.tutorial.stop()
        camera.stop()


if __name__ == "__main__":
    main()
