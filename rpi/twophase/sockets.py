# ################## The code of the server socket which communicates with the client ##################################

from __future__ import annotations

import socket
import sys
import threading
import time
from typing import Any

from rubik_robot.web.controller import robot_controller
from rubik_robot.web.server import RubikWebHandler, ThreadedHTTPServer
import twophase.solver as solver

_HTTP_METHODS = (b"GET ", b"POST ", b"HEAD ", b"OPTIONS", b"PUT ", b"DELETE")


def client_thread(conn: socket.socket, maxlen: int, timeout: int) -> None:
    """Handle raw TCP socket clients (telnet, client_gui.py, scripts)."""
    while True:
        data = []
        while not (ord("\n") in data or ord("\r") in data):
            try:
                a = conn.recv(1024).upper()
                if len(a) == 0:
                    conn.close()
                    return
            except Exception:
                conn.close()
                return
            for i in range(len(a)):
                if a[i] in [
                    ord("\n"),
                    ord("\r"),
                    ord("G"),
                    ord("E"),
                    ord("T"),
                    ord("U"),
                    ord("R"),
                    ord("F"),
                    ord("D"),
                    ord("L"),
                    ord("B"),
                    ord("X"),
                ]:
                    data.append(a[i])

        if not data or data[0] == ord("X"):
            break

        defstr = "".join(chr(i) for i in data if chr(i) > chr(32))
        qpos = defstr.find("GET")
        if qpos >= 0:
            defstr = defstr[qpos + 3 : qpos + 57]
            clean_def = defstr.strip()
            if len(clean_def) == 54:
                try:
                    robot_controller.set_cube(clean_def)
                except Exception:
                    pass
            reply = (
                "HTTP/1.1 200 OK\n\n"
                "<html><head><title>Answer from Cubesolver</title></head><body>\n"
                f"{solver.solve(defstr, maxlen, timeout)}\n"
                "</body></html>\n"
            )
            conn.sendall(reply.encode())
            conn.close()
            return
        else:
            try:
                # If this is a valid 54-char cube from camera detection (run_vision_gui.py), sync to 3D model!
                clean_def = defstr.strip()
                if len(clean_def) == 54:
                    try:
                        robot_controller.set_cube(clean_def)
                        robot_controller.log("INFO", f"Cube imported from camera detection: {clean_def[:15]}...")
                    except Exception as ex:
                        robot_controller.log("ERR", f"Failed to sync cube: {ex}")

                solution = solver.solve(defstr, maxlen, timeout)
                reply = (solution + "\n").encode()
                conn.sendall(reply)
                robot_controller.log("INFO", f"TCP client solved: {solution}")
            except Exception as e:
                robot_controller.log("ERR", f"Error in raw TCP client solve: {e}")
                conn.close()
                return

    conn.close()


class DualProtocolServer(ThreadedHTTPServer):
    """Server listening on port 8080 that transparently handles both HTTP (3D web model,
    REST API, Server-Sent Events) and legacy raw TCP socket connections."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], maxlen: int = 20, timeout: int = 3) -> None:
        self.maxlen = maxlen
        self.timeout = timeout
        super().__init__(server_address, RubikWebHandler)

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        try:
            # Peek up to 16 bytes to check if this is an HTTP request
            peek_data = request.recv(16, socket.MSG_PEEK)
            is_http = any(peek_data.startswith(m) for m in _HTTP_METHODS)
            if is_http:
                self.finish_request(request, client_address)
            else:
                client_thread(request, self.maxlen, self.timeout)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def server_start(args: list[str] | tuple[Any, ...]) -> None:
    port = int(args[1]) if len(args) > 1 else 8080
    maxlen = int(args[2]) if len(args) > 2 else 20
    timeout = int(args[3]) if len(args) > 3 else 3

    print(f"Server starting on http://localhost:{port} (HTTP & TCP dual-mode)")
    robot_controller.log("INFO", f"Server started on port {port}")

    server = DualProtocolServer(("", port), maxlen=maxlen, timeout=timeout)
    print(f"Web interface & 3D model available at: http://localhost:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()
        server.server_close()
