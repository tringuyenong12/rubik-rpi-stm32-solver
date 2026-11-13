"""Verify complete web workflows without opening a camera or serial device."""

import json
import inspect
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import cv2
import numpy as np

from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE
from rubik_robot.web.camera import Camera
from rubik_robot.web.cube import apply_moves, inverse_moves, scramble_for, solution_for, validated_cube
from rubik_robot.web.scan import assemble_faces, camera_face, canonical_face, fixed_route
from rubik_robot.web.studio_server import make_handler
from rubik_robot.web.service import Service
from rubik_robot.web.vision import COLORS, StableFace, classify_bgr_color, sample_face
from rubik_robot.web import camera_tutorial as tutorial
from rubik_robot.web import tutorial_moves

EXAMPLE = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"
BGR = {"white": [235, 235, 235], "red": [25, 25, 220], "green": [25, 180, 25],
       "yellow": [20, 220, 220], "orange": [20, 125, 240], "blue": [220, 65, 20]}


def color_faces(state):
    """Input: cube state. Output: six grids using the UI's physical colors."""
    return {f: [COLORS[v] for v in state[i * 9:i * 9 + 9]] for i, f in enumerate(FACE_ORDER)}


class TestWebCube(unittest.TestCase):
    """Mathematical state, scramble and solver integrity checks."""

    def test_all_moves_and_inverse(self):
        """Input: each basic move. Output: move/inverse and four turns restore identity."""
        for face in FACE_ORDER:
            self.assertEqual(apply_moves(SOLVED_CUBE, [face] * 4), SOLVED_CUBE)
            for suffix in ("", "'", "2"):
                moves = [face + suffix]
                self.assertEqual(apply_moves(apply_moves(EXAMPLE, moves), inverse_moves(moves)), EXAMPLE)

    def test_three_levels_reproduce_and_solve(self):
        """Input: all difficulty levels. Output: correct lengths and verified inverse/solution."""
        for level, length in [("easy", 5), ("medium", 12), ("hard", 22)]:
            task = scramble_for(level, 42)
            self.assertEqual(len(task["scramble"]), length)
            self.assertEqual(apply_moves(SOLVED_CUBE, task["scramble"]), task["state"])
            self.assertEqual(apply_moves(task["state"], task["inverse"]), SOLVED_CUBE)
            self.assertEqual(apply_moves(task["state"], task["solution"]["moves"]), SOLVED_CUBE)
            self.assertEqual(len(task["scramble_uart"]), length)
            self.assertTrue(all(line.startswith("TURN ") for line in task["scramble_uart"]))
            self.assertNotEqual(task["state"], SOLVED_CUBE)

    def test_rejects_bad_moves_and_impossible_state(self):
        """Input: bad token, swapped centers, one flipped edge. Output: explicit errors."""
        with self.assertRaises(ValueError):
            apply_moves(SOLVED_CUBE, "R4")
        state = list(SOLVED_CUBE)
        state[5], state[10] = state[10], state[5]
        with self.assertRaises(ValueError):
            validated_cube("".join(state))
        state = list(SOLVED_CUBE)
        state[4], state[13] = state[13], state[4]
        with self.assertRaises(ValueError):
            solution_for("".join(state))



class TestWebVision(unittest.TestCase):
    """Controlled images verify color classification, calibration and rejection."""

    def test_bgr_color_classification(self):
        """Input: representative BGR samples. Output: correct six color labels."""
        for color, bgr in BGR.items():
            self.assertEqual(classify_bgr_color(np.array(bgr)), color)

    def test_calibrated_grid_and_uncertainty(self):
        """Input: nine synthetic stickers and an ambiguous sample. Output: correct labels/rejection."""
        image = np.zeros((300, 300, 3), dtype=np.uint8)
        colors = ["white", "red", "green", "yellow", "orange", "blue", "red", "green", "white"]
        profile = {color: cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2LAB)[0, 0].tolist() for color, bgr in BGR.items()}
        for i, color in enumerate(colors):
            row, col = divmod(i, 3)
            image[row * 100 + 8:row * 100 + 92, col * 100 + 8:col * 100 + 92] = BGR[color]
        sample = sample_face(image, [[0, 0], [1, 0], [1, 1], [0, 1]], profile)
        self.assertEqual(sample["colors"], colors)
        self.assertTrue(sample["ready"])
        duplicate_profile = {color: profile["red"] for color in profile}
        self.assertFalse(sample_face(image, [[0, 0], [1, 0], [1, 1], [0, 1]], duplicate_profile)["ready"])
        blurred = cv2.GaussianBlur(image, (61, 61), 0)
        self.assertFalse(sample_face(blurred, [[0, 0], [1, 0], [1, 1], [0, 1]], profile)["ready"])

    def test_stability_requires_consecutive_reliable_frames(self):
        """Input: matching, changing and low-confidence frames. Output: gate resets correctly."""
        gate = StableFace()
        sample = {"colors": ["white"] * 9, "ready": True}
        for i in range(8):
            self.assertEqual(gate.update(sample), i + 1)
        self.assertEqual(gate.update({"colors": ["red"] * 9, "ready": True}), 1)
        self.assertEqual(gate.update({"colors": ["red"] * 9, "ready": False}), 0)


class TestWebScan(unittest.TestCase):
    """Verify geometry with nonuniform faces; uniform solved faces cannot expose rotation bugs."""

    def setUp(self):
        """Input: none. Output: isolated service and calibration directory."""
        self.temp = tempfile.TemporaryDirectory()
        self.camera = Camera()
        self.service = Service(self.camera, Path(self.temp.name) / "profile.json")

    def tearDown(self):
        """Input: test resources. Output: cleaned temporary directory."""
        self.temp.cleanup()

    def test_route_all_faces_round_trip(self):
        """Input: mixed cube and whole-cube poses. Output: exact 54-sticker reconstruction."""
        route = fixed_route()
        self.assertEqual([s["face"] for s in route if s["kind"] == "capture"], list("UFDBRL"))
        original = color_faces(EXAMPLE)
        recovered = {}
        for step in route:
            if step["kind"] == "capture":
                face = step["face"]
                raw = camera_face(original[face], face, step["orientation"])
                recovered[face] = canonical_face(raw, face, step["orientation"])
        expected_indices = {"U": list(range(9)), "F": list(range(9)), "D": list(range(9)),
                            "B": list(reversed(range(9))), "R": [6, 3, 0, 7, 4, 1, 8, 5, 2],
                            "L": [2, 5, 8, 1, 4, 7, 0, 3, 6]}
        for step in route:
            if step["kind"] == "capture":
                self.assertEqual(canonical_face(list(range(9)), step["face"], step["orientation"]),
                                 expected_indices[step["face"]])
        self.assertEqual(assemble_faces(recovered), EXAMPLE)
        self.assertEqual(route[-1]["uart"], "REORIENT Z -1 800")

    def test_demo_full_workflow_and_stale_ack(self):
        """Input: full simulated scan. Output: wait for DONE, reconstructed state and solution."""
        self.service.start_scan("demo", EXAMPLE)
        self.service.demo_step()
        self.assertEqual(self.service.scan["status"], "waiting_done")
        with self.assertRaises(ValueError):
            self.service.acknowledge(999, "DONE")
        with self.assertRaises(ValueError):
            self.service.acknowledge(self.service.scan_public()["next"]["id"], "OK")
        for _ in range(20):
            if self.service.scan["status"] == "complete":
                break
            self.service.demo_step()
        self.assertEqual(self.service.scan["status"], "complete")
        self.assertEqual(self.service.last_solution["state"], EXAMPLE)
        self.assertEqual(apply_moves(EXAMPLE, self.service.last_solution["moves"]), SOLVED_CUBE)
        self.assertEqual(len(self.service.scan["faces"]), 6)

    def test_real_scan_requires_calibration_and_does_not_fake_done(self):
        """Input: real mode without samples then waiting command. Output: explicit gates."""
        with self.assertRaises(ValueError):
            self.service.start_scan("external")
        self.camera.profile = {c: [100, 100, 100] for c in COLORS.values()}
        self.service.start_scan("external")
        self.service._record_scan(["white"] * 9)
        self.service.tick()
        self.assertEqual(self.service.scan["status"], "waiting_done")
        self.assertEqual(self.service.scan_public()["next"]["uart"], "REORIENT X 1 800")

    def test_synthetic_camera_full_scan_to_solution(self):
        """Input: six rendered camera images and real ACK gates. Output: exact mixed cube/solution."""
        self.camera.profile = {color: cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2LAB)[0, 0].tolist()
                               for color, bgr in BGR.items()}
        self.service.start_scan("external")
        faces = color_faces(EXAMPLE)
        for _ in range(13):
            step = self.service.scan_public()["next"]
            if step["kind"] == "reorient":
                self.service.acknowledge(step["id"], "DONE")
                continue
            raw = camera_face(faces[step["face"]], step["face"], step["orientation"])
            image = np.zeros((300, 300, 3), dtype=np.uint8)
            for i, color in enumerate(raw):
                row, col = divmod(i, 3)
                image[row * 100 + 8:row * 100 + 92, col * 100 + 8:col * 100 + 92] = BGR[color]
            sample = sample_face(image, [[0, 0], [1, 0], [1, 1], [0, 1]], self.camera.profile)
            self.assertTrue(sample["ready"])
            gate = StableFace()
            for _ in range(8):
                sample["stable"] = gate.update(sample)
            sample.update(seq=self.service.after_seq + 1, timestamp=time.monotonic())
            self.camera.sample = sample
            self.service.ready_at = 0
            self.service.tick()
        self.assertEqual(self.service.scan["status"], "complete")
        self.assertEqual(self.service.last_solution["state"], EXAMPLE)
        self.assertEqual(apply_moves(EXAMPLE, self.service.last_solution["moves"]), SOLVED_CUBE)



class TestWebAPI(unittest.TestCase):
    """Exercise real HTTP endpoints and the browser's three feature paths."""

    def setUp(self):
        """Input: none. Output: isolated localhost server on a free port."""
        self.temp = tempfile.TemporaryDirectory()
        self.service = Service(Camera(), Path(self.temp.name) / "profile.json")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.service))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        """Input: test server. Output: closed socket/thread and temporary directory."""
        self.service.tutorial.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, body=None):
        """Input: API path and optional JSON. Output: decoded response."""
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=20) as response:
            return json.load(response)

    def test_static_and_three_features(self):
        """Input: HTTP tutorial/scramble/scan requests. Output: correct results for all modes."""
        for path in ("/", "/app.js", "/styles.css"):
            with urlopen(self.base + path) as response:
                self.assertEqual(response.status, 200)
                self.assertTrue(response.read())
        for face, colors in color_faces(EXAMPLE).items():
            self.request("/api/faces/capture", {"face": face, "colors": colors})
        self.service.tutorial.video_factory = FakeVideo
        guide = self.request("/api/tutorial/start", {"index": 1, "backend": "dshow"})
        self.assertEqual(guide["phase"], "scanning")
        self.assertTrue(self.request("/api/status")["tutorial"]["running"])
        for _ in range(50):
            if self.request("/api/status")["tutorial"]["seq"]:
                break
            time.sleep(0.01)
        with urlopen(self.base + "/api/tutorial/frame.jpg") as response:
            self.assertEqual(response.status, 200)
            self.assertIsNotNone(cv2.imdecode(np.frombuffer(response.read(), np.uint8), cv2.IMREAD_COLOR))
        with self.assertRaises(HTTPError) as camera_busy:
            self.request("/api/camera/start", {"index": 1, "backend": "dshow"})
        self.assertEqual(camera_busy.exception.code, 400)
        self.request("/api/tutorial/stop", {})
        self.assertEqual(self.request("/api/status")["tutorial"]["phase"], "cancelled")
        for level, length in [("easy", 5), ("medium", 12), ("hard", 22)]:
            self.assertEqual(len(self.request("/api/scramble", {"level": level, "seed": 1})["scramble"]), length)
        self.request("/api/scan/start", {"mode": "demo", "state": EXAMPLE})
        for _ in range(13):
            result = self.request("/api/scan/demo-step", {})
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["solution"]["state"], EXAMPLE)
        self.assertFalse(self.request("/api/status")["camera"]["running"])

    def test_invalid_state_and_input_return_errors(self):
        """Input: invalid API payloads and traversal. Output: errors, never movement payloads."""
        for path, body in [("/api/solve", {"state": "U"}), ("/api/scramble", {"level": "expert"}),
                           ("/api/scan/ack", {"id": 1, "result": "DONE"})]:
            with self.assertRaises(HTTPError) as error:
                self.request(path, body)
            self.assertEqual(error.exception.code, 400)
        with self.assertRaises(HTTPError):
            urlopen(self.base + "/../LICENSE")


class FakeVideo:
    """Deterministic capture for tutorial tests; never opens hardware."""

    def __init__(self):
        """Input: none. Output: readable black frames and a release flag."""
        self.released = False

    def read(self):
        """Input: none. Output: a fresh BGR frame."""
        return True, np.zeros((240, 320, 3), dtype=np.uint8)

    def set(self, key, value):
        """Input: camera property/value. Output: accepted test configuration."""
        return True

    def release(self):
        """Input: none. Output: recorded handle release."""
        self.released = True


class TestCompleteCameraTutorial(unittest.TestCase):
    """Exercise full move bodies and the entire scan/dispatch flow, not a reduced guide."""

    def setUp(self):
        """Input: none. Output: isolated runtime adapters and no physical camera."""
        self.session = tutorial.CameraTutorial(FakeVideo)
        self.image_api = tutorial._ImageAPI(self.session)
        self.patches = [patch.object(tutorial, "_runtime", self.session),
                        patch.object(tutorial, "cv2", self.image_api),
                        patch.object(tutorial_moves, "cv2", self.image_api),
                        patch.object(tutorial_moves, "stats", tutorial.stats),
                        patch.object(tutorial_moves, "print", lambda *args: None, create=True),
                        patch.object(tutorial, "print", lambda *args: None, create=True),
                        patch.object(tutorial._ImageAPI, "waitKey", return_value=-1)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def faces(self, state):
        """Input: URFDLB state. Output: six mutable 1x9 arrays for full move routines."""
        return [np.array([list(state[i * 9:i * 9 + 9])]) for i in range(6)]

    def detected_front(self, frame):
        """Input: image from a move routine. Output: that routine's predicted visible face."""
        values = inspect.currentframe().f_back.f_locals["front_face"]
        boxes = [[0, 0, 0, 0, 0, 30 + (i % 3) * 50, 30 + (i // 3) * 50, 40, 40] for i in range(9)]
        return np.asarray(values).ravel().copy(), np.array(boxes)

    def test_all_twelve_full_turn_routines_match_cube_model(self):
        """Input: mixed cube and every quarter turn. Output: correct state after 10-frame verification."""
        with patch.object(tutorial_moves, "detect_face", self.detected_front):
            for face, name in [("R", "right"), ("L", "left"), ("F", "front"),
                               ("B", "back"), ("U", "up"), ("D", "down")]:
                for suffix, direction in [("", "cw"), ("'", "ccw")]:
                    with self.subTest(move=face + suffix):
                        result = getattr(tutorial_moves, name + "_" + direction)(
                            FakeVideo(), tutorial._VideoOutput(), *self.faces(EXAMPLE))
                        state = "".join(str(c) for array in result for c in array.ravel())
                        self.assertEqual(state, apply_moves(EXAMPLE, face + suffix))

    def test_whole_cube_view_changes_are_inverse(self):
        """Input: right-view then front-view actions. Output: original six arrays restored."""
        with patch.object(tutorial_moves, "detect_face", self.detected_front):
            faces = tutorial_moves.turn_to_right(FakeVideo(), tutorial._VideoOutput(), *self.faces(EXAMPLE))
            faces = tutorial_moves.turn_to_front(FakeVideo(), tutorial._VideoOutput(), *faces)
        self.assertEqual("".join(str(c) for array in faces for c in array.ravel()), EXAMPLE)

    def test_arrow_is_drawn_until_observed_move_matches(self):
        """Input: ten unchanged frames then ten correct frames. Output: real annotated JPEG and verified move."""
        calls = 0
        annotated_frames = []
        publish = self.image_api.imshow

        def publish_frame(title, frame):
            """Input: rendered frame. Output: JPEG plus evidence of an actual red arrow."""
            publish(title, frame)
            decoded = cv2.imdecode(np.frombuffer(self.session.jpeg, np.uint8), cv2.IMREAD_COLOR)
            annotated_frames.append(int(decoded[:, :, 2].sum()))

        def observe(frame):
            """Input: frame. Output: old front first, predicted front after the arrow appears."""
            nonlocal calls
            calls += 1
            local = inspect.currentframe().f_back.f_locals
            values = local["temp"] if calls <= 10 else local["front_face"]
            boxes = [[0, 0, 0, 0, 0, 30 + (i % 3) * 50, 30 + (i // 3) * 50, 40, 40] for i in range(9)]
            return np.asarray(values).ravel().copy(), np.array(boxes)

        with patch.object(tutorial_moves, "detect_face", observe), \
                patch.object(self.image_api, "imshow", side_effect=publish_frame):
            result = tutorial_moves.right_cw(FakeVideo(), tutorial._VideoOutput(), *self.faces(EXAMPLE))
        self.assertEqual(calls, 20)
        self.assertEqual("".join(str(c) for array in result for c in array.ravel()), apply_moves(EXAMPLE, "R"))
        self.assertTrue(any(value > 0 for value in annotated_frames))

    def execute_complete_flow(self, state, solution):
        """Input: starting state and solver response. Output: all original scan and dispatch stages run."""
        code_by_face = {"U": 1, "R": 5, "F": 4, "D": 2, "L": 6, "B": 3}
        grids = {face: np.array([[code_by_face[c] for c in state[i * 9:i * 9 + 9]]])
                 for i, face in enumerate(FACE_ORDER)}
        session = self.session
        session.phase, session.instruction = "scanning", "Show Front Face"
        session.faces, session.solution = {}, None
        session.move_index = 0
        order = []
        record = session.record_face

        def record_face(prompt, values):
            """Input: completed scan. Output: record scan order and actual five-vote face."""
            order.append(tutorial._PROMPT_FACES[prompt])
            record(prompt, values)

        def detect(frame):
            """Input: frame. Output: requested scan face or exact predicted move face."""
            caller = inspect.currentframe().f_back
            if caller.f_code.co_name == "find_face":
                values = grids[tutorial._PROMPT_FACES[session.instruction]]
            else:
                values = caller.f_locals["front_face"]
            boxes = [[0, 0, 0, 0, 0, 30 + (i % 3) * 50, 30 + (i // 3) * 50, 40, 40] for i in range(9)]
            return np.asarray(values).ravel().copy(), np.array(boxes)

        def solve(scanned):
            """Input: scanned cube. Output: specified solution in standard notation."""
            self.assertEqual(scanned, state)
            session.solution = {"state": state, "moves": solution.split(), "count": len(solution.split()), "uart": []}
            session.phase = "guiding"
            return solution

        class FastDateTime:
            """Advance the existing inter-face timers without real waiting."""
            counter = 0

            @classmethod
            def now(cls):
                """Input: none. Output: monotonically advancing datetime."""
                cls.counter += 1
                return datetime(2020, 1, 1) + timedelta(seconds=cls.counter)

        with patch.object(tutorial, "detect_face", detect), patch.object(tutorial_moves, "detect_face", detect), \
                patch.object(tutorial, "datetime", FastDateTime), patch.object(tutorial.time, "sleep", return_value=None), \
                patch.object(tutorial._Solver, "solve", side_effect=solve), patch.object(session, "record_face", side_effect=record_face):
            tutorial.run_tutorial()
        self.assertEqual(order, list("FUDRLB"))
        self.assertEqual(session.phase, "complete")
        return session

    def test_complete_dispatch_for_all_eighteen_moves(self):
        """Input: each solvable single-token case. Output: scan, half-turn/back-view flow and completion."""
        for face in FACE_ORDER:
            for suffix in ("", "'", "2"):
                token = face + suffix
                with self.subTest(move=token):
                    state = apply_moves(SOLVED_CUBE, inverse_moves([token]))
                    session = self.execute_complete_flow(state, token)
                    self.assertEqual(session.move_index, 1)

    def test_already_solved_finishes_without_unbound_solution(self):
        """Input: solved faces. Output: completed empty solution without entering move dispatch."""
        session = self.execute_complete_flow(SOLVED_CUBE, "")
        self.assertEqual(session.solution["moves"], [])
        self.assertEqual(session.solution["state"], SOLVED_CUBE)

    def test_mode_preserves_legacy_row_shape_and_tie_rule(self):
        """Input: tied votes. Output: one-row mode, smallest code, matching counts."""
        values, counts = tutorial.stats.mode([[2, 4], [1, 4]])
        self.assertEqual(values.tolist(), [[1, 4]])
        self.assertEqual(counts.tolist(), [[1, 2]])

    def test_full_detector_recognizes_nine_sticker_image(self):
        """Input: nine colored squares. Output: exact nine numeric colors and contour boxes."""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        codes = [1, 2, 3, 4, 5, 6, 1, 4, 3]
        bgr = {1: BGR["white"], 2: BGR["yellow"], 3: BGR["blue"],
               4: BGR["green"], 5: BGR["red"], 6: BGR["orange"]}
        for i, code in enumerate(codes):
            x, y = 180 + (i % 3) * 55, 100 + (i // 3) * 55
            cv2.rectangle(image, (x, y), (x + 32, y + 32), bgr[code], -1)
        values, boxes = tutorial.detect_face(image)
        self.assertEqual(np.asarray(values).tolist(), codes)
        self.assertEqual(len(boxes), 9)


if __name__ == "__main__":
    unittest.main()
