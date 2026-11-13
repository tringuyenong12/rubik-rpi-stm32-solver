from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import mimetypes
from pathlib import Path
import queue
import re
import socketserver
from typing import Any
from urllib.parse import parse_qs, urlparse

from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string
from rubik_robot.solver.kociemba_solver import solve_cube
from rubik_robot.web.controller import robot_controller

_STATIC_DIR = Path(__file__).resolve().parent / "static"

_CUBE_REGEX = re.compile(r"^/([URFDLB]{54})$", re.IGNORECASE)


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server supporting persistent SSE streaming connections."""
    daemon_threads = True
    allow_reuse_address = True


class RubikWebHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for 3D Rubik model visualizer, REST API, and SSE events."""

    server_version = "RubikRobotWeb/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy HTTP request logging in terminal
        pass

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept")

    def _send_json(self, data: Any, status: int = 200) -> None:
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_error_json(self, message: str, status: int = 400) -> None:
        self._send_json({"error": message}, status=status)

    def _read_json_body(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length")
        if not length_header:
            return {}
        try:
            length = int(length_header)
            raw = self.rfile.read(length)
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        # 1. API: Server-Sent Events stream
        if path == "/api/events":
            self._handle_sse_stream()
            return

        # 2. API: Status
        if path == "/api/status":
            self._send_json(robot_controller.get_status())
            return

        # 3. Check for 54-char cube string in URL path (legacy support)
        cube_match = _CUBE_REGEX.match(path)
        if cube_match:
            cube_str = cube_match.group(1).upper()
            try:
                validate_cube_string(cube_str)
                # If requested as legacy HTML or raw text
                if "legacy" in query.get("format", []) or "text/plain" in self.headers.get("Accept", ""):
                    sol = solve_cube(cube_str)
                    html = (
                        "HTTP/1.1 200 OK\n\n"
                        "<html><head><title>Answer from Cubesolver</title></head><body>\n"
                        f"{sol}\n"
                        "</body></html>\n"
                    )
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html.encode("utf-8"))
                    return

                # Otherwise, set cube in controller and redirect to home with preloaded cube
                robot_controller.set_cube(cube_str)
                self.send_response(HTTPStatus.FOUND)
                self.send_header("Location", f"/?cube={cube_str}")
                self.end_headers()
                return
            except Exception as e:
                self._send_error_json(str(e), 400)
                return

        # 4. Static files
        self._serve_static_file(path)

    def do_POST(self) -> None:
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        try:
            body = self._read_json_body()
        except ValueError as ex:
            self._send_error_json(str(ex), 400)
            return

        try:
            if path == "/api/solve":
                result = robot_controller.start_solve(
                    cube_str=body.get("cube"),
                    duration_ms=body.get("duration_ms"),
                    face_turn_command=body.get("face_turn_command"),
                    hardware_mode=body.get("mode"),
                    port=body.get("port"),
                )
                self._send_json(result)
            elif path == "/api/scramble":
                level = body.get("level", "medium")
                result = robot_controller.scramble_cube(level=level)
                self._send_json(result)
            elif path == "/api/move":
                move_token = body.get("move")
                if not move_token:
                    self._send_error_json("Missing 'move' field", 400)
                    return
                result = robot_controller.apply_single_move(move_token)
                self._send_json(result)
            elif path == "/api/cube":
                cube_str = body.get("cube")
                if not cube_str:
                    self._send_error_json("Missing 'cube' field", 400)
                    return
                result = robot_controller.set_cube(cube_str)
                self._send_json(result)
            elif path == "/api/reset":
                result = robot_controller.reset_cube()
                self._send_json(result)
            elif path == "/api/pause":
                result = robot_controller.pause()
                self._send_json(result)
            elif path == "/api/resume":
                result = robot_controller.resume()
                self._send_json(result)
            elif path == "/api/step":
                result = robot_controller.step()
                self._send_json(result)
            elif path == "/api/stop":
                result = robot_controller.stop()
                self._send_json(result)
            else:
                self._send_error_json(f"Unknown endpoint: {path}", 404)
        except Exception as e:
            self._send_error_json(str(e), 500)

    def _serve_static_file(self, path: str) -> None:
        """Serve HTML, JS, CSS, and static assets from _STATIC_DIR."""
        if path in {"", "/"}:
            file_path = _STATIC_DIR / "index.html"
        elif path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = _STATIC_DIR / rel_path
        else:
            file_path = _STATIC_DIR / path.lstrip("/")

        # Security check: ensure path is within _STATIC_DIR
        try:
            resolved = file_path.resolve()
            if not resolved.is_relative_to(_STATIC_DIR.resolve()):
                self._send_error_json("Forbidden", 403)
                return
        except Exception:
            self._send_error_json("Not found", 404)
            return

        if not resolved.is_file():
            # If not found and not an API call, fallback to index.html for SPA-style routing
            if path in {"", "/index.html"}:
                self._send_error_json("Index file not found", 404)
                return
            file_path = _STATIC_DIR / "index.html"
            resolved = file_path.resolve()
            if not resolved.is_file():
                self._send_error_json("Not found", 404)
                return

        mime_type, _ = mimetypes.guess_type(str(resolved))
        if mime_type is None:
            mime_type = "application/octet-stream"

        try:
            content = resolved.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type or "json" in mime_type else mime_type)
            self.send_header("Content-Length", str(len(content)))
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_error_json(f"Error reading file: {e}", 500)

    def _handle_sse_stream(self) -> None:
        """Stream real-time events over Server-Sent Events (SSE)."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self._send_cors_headers()
        self.end_headers()

        event_queue = robot_controller.subscribe()
        try:
            # Immediately send initial status
            init_data = json.dumps(robot_controller.get_status(), ensure_ascii=False)
            self.wfile.write(f"event: status\ndata: {init_data}\n\n".encode("utf-8"))
            self.wfile.flush()

            while True:
                try:
                    event = event_queue.get(timeout=15.0)
                    evt_type = event.get("event", "message")
                    evt_data = json.dumps(event.get("data", {}), ensure_ascii=False)
                    msg = f"event: {evt_type}\ndata: {evt_data}\n\n"
                    self.wfile.write(msg.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive ping comment
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, socketserver.socket.error):
            pass
        finally:
            robot_controller.unsubscribe(event_queue)


def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> ThreadedHTTPServer:
    """Create and start the threaded HTTP web server."""
    server = ThreadedHTTPServer((host, port), RubikWebHandler)
    return server
