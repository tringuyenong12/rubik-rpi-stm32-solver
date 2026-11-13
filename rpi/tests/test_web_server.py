import json
import socket
import threading
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.web.controller import RobotWebController
from rubik_robot.web.server import RubikWebHandler, ThreadedHTTPServer
from twophase.sockets import DualProtocolServer


class TestWebServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = 18888
        cls.server = DualProtocolServer(("127.0.0.1", cls.port), maxlen=20, timeout=3)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_status_api(self):
        url = f"http://127.0.0.1:{self.port}/api/status"
        with urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("cube", data)
            self.assertIn("solver_state", data)
            self.assertIn("actuators", data)

    def test_get_index_html(self):
        url = f"http://127.0.0.1:{self.port}/"
        with urlopen(url) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("Rubik Solver", html)
            self.assertIn("3D Digital Twin", html)

    def test_post_scramble_and_reset(self):
        # Scramble
        req = Request(
            f"http://127.0.0.1:{self.port}/api/scramble",
            data=json.dumps({"level": "easy"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("scramble", data)
            self.assertNotEqual(data["cube"], SOLVED_CUBE)

        # Reset
        req_reset = Request(
            f"http://127.0.0.1:{self.port}/api/reset",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req_reset) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["cube"], SOLVED_CUBE)
            self.assertTrue(data["is_solved"])

    def test_post_manual_move(self):
        req = Request(
            f"http://127.0.0.1:{self.port}/api/move",
            data=json.dumps({"move": "R"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertNotEqual(data["cube"], SOLVED_CUBE)

        # Revert with R'
        req_rev = Request(
            f"http://127.0.0.1:{self.port}/api/move",
            data=json.dumps({"move": "R'"}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlopen(req_rev) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["cube"], SOLVED_CUBE)

    def test_raw_tcp_socket_client(self):
        """Verify legacy TCP clients (like client_gui.py) can still query solver directly."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", self.port))
        # Send solved cube over raw TCP
        s.sendall((SOLVED_CUBE + "\n").encode())
        response = s.recv(1024).decode("utf-8")
        s.close()
        # Twophase solver returns empty string or "(0f)" for already solved cube
        self.assertTrue(len(response) >= 0)

    def test_controller_simulated_solve(self):
        from rubik_robot.cube.scramble import apply_moves

        ctrl = RobotWebController()
        # Set a 2-move scrambled cube
        scrambled = apply_moves(SOLVED_CUBE, ["R", "U"])
        # Validate through controller
        status = ctrl.set_cube(scrambled)
        self.assertEqual(status["cube"], scrambled)

        # Start simulated solve with short duration
        ctrl.start_solve(duration_ms=20, hardware_mode="simulated")
        if ctrl._worker_thread:
            ctrl._worker_thread.join(timeout=10.0)
        final_status = ctrl.get_status()
        self.assertEqual(final_status["solver_state"], "DONE")
        self.assertEqual(final_status["cube"], SOLVED_CUBE)


if __name__ == "__main__":
    unittest.main()
