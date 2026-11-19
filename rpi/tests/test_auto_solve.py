"""Check pose geometry, six-face transactions, cancellation and independent navigation."""

from collections import Counter
from itertools import permutations, product
from threading import Event
from types import SimpleNamespace
import time
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np

from rubik_robot.auto_solve import (AutoCamera, AutoSolveCancelled, FACE_COLORS, SCAN_ROUTE,
                                    execute_auto_solve, prepare_machine_cube, rotate_grid, scan_commands)
from rubik_robot.auto_solve_panel import AutoSolveWorkspace
from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.scramble_panel import ScrambleWorkspace
from rubik_robot.vision.solve_guide import NORMALS, RIGHT, DOWN, apply_move, cube_faces


SCRAMBLED = 'DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL'
SOLUTION = "D2 L' D' L2 U R2 F B L B D' B2 R2 U' R2 U' F2 R2 U' L2"
PROTOTYPES = dict(zip(FACE_COLORS.values(), ((30, 230, 220), (60, 220, 190), (1, 230, 210),
                                           (0, 10, 220), (115, 230, 200), (17, 230, 230))))


class TestAutoFlow(unittest.TestCase):
    def setUp(self):
        """Input: known scrambled model. Output: fake camera/UART and ordered transaction log."""
        self.cancel = Event()
        self.trace = []
        self.faces = cube_faces(SCRAMBLED)
        self.physical_cube = SCRAMBLED
        self.link = Mock()
        self.link.request_completed.side_effect = self.complete
        self.link.request_scan.side_effect = self.complete_scan

    def complete(self, command, timeout_s):
        """Input: frame. Output: matching simulated completion recorded before capture."""
        self.trace.append(('done', command.to_wire()))
        if command.name == 'MOVE':
            for face, turns in command.moves:
                self.physical_cube = apply_move(self.physical_cube, face + {1: '', -1: "'", 2: '2'}[turns])
        return 'OK PONG' if command.name == 'PING' else f'DONE {command.name}'

    def complete_scan(self, body):
        self.trace.append(('done', body))
        return 'DONE'

    def capture(self, pose, seen_centers=()):
        """Input: absolute camera pose. Output: corresponding raw optical colors/HSV."""
        self.trace.append(('capture', pose.face))
        colors = rotate_grid(cube_faces(self.physical_cube)[FACE_COLORS[pose.face]], -pose.correction)
        return colors, tuple(PROTOTYPES[color] for color in colors)

    def emit(self, kind, value):
        """Input: host event. Output: append it to the transaction log."""
        self.trace.append((kind, value))

    def solver(self, host, port, cube):
        """Input: prepared cube. Output: independently known solving sequence."""
        self.trace.append(('solve', cube))
        self.assertEqual(cube, SCRAMBLED)
        return SOLUTION

    def run_flow(self, **overrides):
        """Input: optional fake overrides. Output: run the actual orchestration core."""
        settings = dict(link=self.link, capture=self.capture, host='localhost', port=8080,
                        cancel=self.cancel, emit=self.emit, solver=self.solver)
        settings.update(overrides)
        return execute_auto_solve(**settings)

    def test_scan_restore_solve_send_transaction(self):
        """Input: all six raw camera views. Output: exact original state and verified TURN plan."""
        result = self.run_flow()
        self.assertEqual(result['cube'], SCRAMBLED)
        self.assertEqual([value for kind, value in self.trace if kind == 'capture'], list('URFDLB' * 2))
        for index, (kind, face) in enumerate(self.trace):
            if kind == 'capture':
                self.assertEqual(self.trace[index-1], ('status', f'Capturing machine position {face} — any new center color accepted...'))
                if face != 'U':
                    self.assertEqual(self.trace[index-2], ('done', f'RUBIK SCAN_POSE {face}'))
        initial = next(i for i, item in enumerate(self.trace) if item == ('capture', 'U'))
        ping = next(i for i, item in enumerate(self.trace) if item == ('command', 'RUBIK PING'))
        self.assertLess(ping, initial)
        solved_at = next(i for i, item in enumerate(self.trace) if item[0] == 'solve')
        previous_commands = [v for k, v in self.trace[:solved_at] if k == 'done']
        self.assertEqual(previous_commands[-1], 'RUBIK SCAN_POSE U')
        self.assertTrue(any(k == 'scan_complete' for k, _ in self.trace[:solved_at]))
        exported = next(i for i, item in enumerate(self.trace) if item[0] == 'solution')
        first_turn = next(i for i, item in enumerate(self.trace) if item[0] == 'command' and item[1].startswith('RUBIK MOVE'))
        self.assertLess(exported, first_turn)
        self.assertEqual(len(result['uart'].splitlines()),
                         sum(2 if token.endswith('2') else 1 for token in SOLUTION.split()))
        self.assertIn('RUBIK MOVE F\nRUBIK MOVE B\n', result['uart'])
        self.assertEqual([v for k, v in self.trace if k == 'move'][-1][2], cube_faces(SOLVED_CUBE))

    def test_fixed_route_geometry_and_restore(self):
        """Input: signed whole-cube X/Z rotations. Output: correct face-up and image corrections."""
        rx = np.array(((1, 0, 0), (0, 0, 1), (0, -1, 0)))  # -90 about +X
        rz = np.array(((0, 1, 0), (-1, 0, 0), (0, 0, 1)))  # -90 about +Z
        transforms = (np.eye(3, dtype=int), rz.T, rx, rx@rx,
                      rz, rx@rx@rx, np.eye(3, dtype=int))
        for pose, rotation in zip(SCAN_ROUTE, transforms):
            index = 'URFDLB'.index(pose.face)
            np.testing.assert_array_equal(rotation@NORMALS[index], (0, 1, 0))
            if not pose.capture:
                np.testing.assert_array_equal(rotation, np.eye(3, dtype=int))
                continue
            raw = np.zeros((3, 3), dtype=int)
            for r in range(3):
                for c in range(3):
                    xyz = rotation@((c-1)*RIGHT[index]+(r-1)*DOWN[index])
                    raw[xyz[2]+1, xyz[0]+1] = r*3+c
            restored = np.rot90(raw, -pose.correction)
            np.testing.assert_array_equal(restored, np.arange(9).reshape(3, 3))
        self.assertEqual(scan_commands().splitlines(), ['RUBIK SCAN_POSE '+f for f in 'RFDLBU'])

    def test_bad_grid_stops_before_uart(self):
        """Input: incomplete initial image. Output: no UART command or server request."""
        with self.assertRaisesRegex(ValueError, 'nine recognized'):
            self.run_flow(capture=lambda pose, **kw: (('red',)*8, None))
        self.link.request_completed.assert_called_once()
        self.link.request_scan.assert_called_once_with('RUBIK SCAN_BEGIN')

    def test_duplicate_center_is_not_saved_twice(self):
        """Input: unchanged face after a pose command. Output: retain first face and stop safely."""
        with self.assertRaisesRegex(ValueError, 'already captured'):
            self.run_flow(capture=lambda pose, **kw: (('red',)*9, None))
        self.assertEqual([v for k, v in self.trace if k == 'done'],
                         ['RUBIK PING', 'RUBIK SCAN_BEGIN', 'RUBIK SCAN_POSE R'])
        saved = [v for k, v in self.trace if k == 'face' and v]
        self.assertEqual(len(saved), 1)
        self.assertEqual(set(saved[0]), {'red'})

    def test_failed_ping_prevents_capture(self):
        self.link.request_completed.side_effect = OSError('COM unavailable')
        capture = Mock()
        with self.assertRaisesRegex(OSError, 'COM unavailable'):
            self.run_flow(capture=capture)
        capture.assert_not_called()
        self.link.request_scan.assert_not_called()

    def test_invalid_cube_cannot_send_solution(self):
        """Input: impossible color counts and no numeric samples. Output: stop after six captures."""
        def bad_capture(pose, seen_centers=()):
            """Input: requested face. Output: impossible stickers with correct center."""
            colors = ['red']*9
            colors[4] = FACE_COLORS[pose.face]
            return colors, None

        with self.assertRaises(ValueError):
            self.run_flow(capture=bad_capture)
        self.assertFalse(any(k == 'solve' or (k == 'command' and v.startswith('RUBIK MOVE')) for k, v in self.trace))

    def test_wrong_solver_result_is_rejected(self):
        """Input: incorrect solving plan. Output: no TURN reaches UART."""
        with self.assertRaisesRegex(ValueError, 'does not solve'):
            self.run_flow(solver=lambda *args: 'U')
        self.assertFalse(any(k == 'command' and v.startswith('RUBIK MOVE') for k, v in self.trace))

    def test_center_calibration_preserves_measured_machine_directions(self):
        """Input: wrong sticker label with accurate HSV. Output: exact original machine state."""
        samples = {center: tuple(PROTOTYPES[color] for color in values) for center, values in self.faces.items()}
        damaged = {center: list(values) for center, values in self.faces.items()}
        for values in damaged.values():
            index = next((i for i, color in enumerate(values) if i != 4 and color == 'orange'), None)
            if index is not None:
                values[index] = 'red'
                break
        cube, recovered, note = prepare_machine_cube(damaged, samples, FACE_COLORS, allow_color_correction=True)
        self.assertEqual(cube, SCRAMBLED)
        self.assertEqual(recovered, self.faces)
        self.assertIn('corrected 1 stickers', note)

    def test_misrotated_scan_is_rejected_instead_of_rotating_faces_silently(self):
        """Input: incorrect camera/pose roll. Output: reject before producing a physical plan."""
        faces = dict(self.faces)
        faces['yellow'] = rotate_grid(faces['yellow'], 1)
        with self.assertRaisesRegex(ValueError, 'directions are inconsistent'):
            prepare_machine_cube(faces, {}, FACE_COLORS)

    def test_cancel_after_pose_does_not_capture_or_retry(self):
        """Input: stop while a pose is moving. Output: wait once, then stop before capture."""
        def stop(body):
            """Input: active command. Output: mark cancellation after its completion."""
            value = self.complete_scan(body)
            if body == 'RUBIK SCAN_POSE R':
                self.cancel.set()
            return value

        self.link.request_scan.side_effect = stop
        with self.assertRaises(AutoSolveCancelled):
            self.run_flow()
        self.assertEqual(self.link.request_scan.call_count, 2)
        self.assertEqual([v for k, v in self.trace if k == 'capture'], ['U'])

    def test_cancel_during_solver_prevents_all_turns(self):
        """Input: stop while TCP solver runs. Output: discard the returned plan without moving."""
        def stop(*args):
            """Input: solver request. Output: cancel before returning a valid result."""
            self.cancel.set()
            return SOLUTION

        with self.assertRaises(AutoSolveCancelled):
            self.run_flow(solver=stop)
        self.assertFalse(any(k == 'solution' for k, _ in self.trace))

    def test_failed_uart_pose_stops_without_capture(self):
        """Input: unsupported firmware pose. Output: no camera capture or later command."""
        self.link.request_scan.side_effect = ['DONE', RuntimeError('ERR UNSUPPORTED')]
        with self.assertRaisesRegex(RuntimeError, 'UNSUPPORTED'):
            self.run_flow()
        self.assertEqual(self.link.request_scan.call_count, 2)

    def test_unsupported_scan_stops_before_capture(self):
        self.link.request_scan.side_effect = RuntimeError('STM32 firmware does not support Auto Solve')
        capture = Mock()
        with self.assertRaisesRegex(RuntimeError, 'firmware does not support'):
            self.run_flow(capture=capture)
        capture.assert_not_called()

    def test_done_without_physical_moves_does_not_report_success(self):
        self.link.request_completed.side_effect = lambda *args, **kwargs: 'DONE'
        with self.assertRaisesRegex(ValueError, 'not solved'):
            self.run_flow()
        self.assertEqual(self.link.request_scan.call_count, 13)

    def test_solved_cube_skips_solver_and_face_moves_but_still_verifies(self):
        self.physical_cube = SOLVED_CUBE
        solver = Mock()
        result = self.run_flow(solver=solver)
        solver.assert_not_called()
        self.assertEqual(result['solution'], '')
        self.link.request_completed.assert_called_once()
        self.assertEqual(self.link.request_scan.call_count, 13)

    def test_all_24_placements_produce_matching_machine_turns(self):
        """Input: 24 spatial rotations of a real scramble. Output: complete scan and correct physical turns."""
        orientations = []
        for axes in permutations(range(3)):
            for signs in product((-1, 1), repeat=3):
                rotation = np.eye(3, dtype=int)[:, axes] * np.asarray(signs)
                if round(np.linalg.det(rotation)) == 1:
                    orientations.append(rotation)
        self.assertEqual(len(orientations), 24)
        for rotation in orientations:
            with self.subTest(rotation=rotation.tolist()):
                face_map, actual_faces = {}, {}
                for index, color in enumerate(FACE_COLORS.values()):
                    target = next(i for i, normal in enumerate(NORMALS)
                                  if np.array_equal(rotation@NORMALS[index], normal))
                    face_map['URFDLB'[index]] = 'URFDLB'[target]
                    grid = ['']*9
                    for sticker, value in enumerate(self.faces[color]):
                        offset = rotation@((sticker%3-1)*RIGHT[index] + (sticker//3-1)*DOWN[index])
                        row = int(offset@DOWN[target])+1
                        column = int(offset@RIGHT[target])+1
                        grid[row*3+column] = value
                    actual_faces['URFDLB'[target]] = tuple(grid)
                centers = {face: values[4] for face, values in actual_faces.items()}
                labels = {color: face for face, color in centers.items()}
                expected_cube = ''.join(labels[value] for face in 'URFDLB' for value in actual_faces[face])
                expected_solution = ' '.join(face_map[token[0]]+token[1:] for token in SOLUTION.split())
                verifying = False

                def capture(pose, seen_centers=()):
                    """Input: known pose. Output: optical grid for this physical placement."""
                    values = ((centers[pose.face],) * 9 if verifying
                              else rotate_grid(actual_faces[pose.face], -pose.correction))
                    self.assertNotIn(values[4], seen_centers)
                    return values, tuple(PROTOTYPES[value] for value in values)

                def solve(host, port, cube):
                    """Input: machine-relative definition. Output: geometrically mapped physical solution."""
                    self.assertEqual(cube, expected_cube)
                    return expected_solution

                trace = []
                link = Mock()
                def emit(kind, value):
                    nonlocal verifying
                    trace.append((kind, value))
                    if kind == 'status' and value.startswith('Solution moves complete.'):
                        verifying = True

                result = self.run_flow(link=link, capture=capture, solver=solve,
                                       emit=emit)
                self.assertEqual(result['position_colors'], centers)
                self.assertEqual(result['solution'], expected_solution)
                self.assertEqual(len([v for k, v in trace if k == 'face'][-1]), 6)
                final_faces = [v for k, v in trace if k == 'move'][-1][2]
                self.assertTrue(all(values == (color,)*9 for color, values in final_faces.items()))
                turns = [face + {1: '', -1: "'", 2: '2'}[count]
                         for call in link.request_completed.call_args_list
                         if call.args[0].name == 'MOVE'
                         for face, count in call.args[0].moves]
                self.assertEqual(Counter(turns), Counter(expected_solution.split()))


class TestAutoCamera(unittest.TestCase):
    def test_real_detector_captures_fresh_stable_face_and_releases_device(self):
        """Input: arbitrary red initial face. Output: stable capture without a yellow-center requirement."""
        from twophase import vision2

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for r in range(3):
            for c in range(3):
                cv2.rectangle(frame, (170+c*60, 130+r*60), (220+c*60, 180+r*60), (0, 0, 240), -1)
        device = Mock()

        def read():
            """Input: device read. Output: paced synthetic camera image."""
            time.sleep(.025)
            return True, frame.copy()

        device.read.side_effect = read
        device.isOpened.return_value = True
        pngs = []
        owner = getattr(vision2, 'camera_thread', None)
        with patch.object(vision2, 'camera_thread', None, create=True), \
                patch.object(vision2.camera_roi, 'load'), \
                patch('rubik_robot.auto_solve.cv2.VideoCapture', return_value=device):
            with AutoCamera((1, None, False), Event(), pngs.append) as camera:
                camera.latest = (0, time.monotonic()-1, np.zeros_like(frame))
                # The real detector must collect twelve frames and hold for
                # 1.5 seconds. Allow the normal capture budget on a busy Pi.
                colors, samples = camera.capture(SCAN_ROUTE[0], settle_s=.05)
                self.assertEqual(colors, ('red',)*9)
                self.assertEqual(len(samples), 9)
                self.assertTrue(pngs[0].startswith(b'\x89PNG'))
                with self.assertRaisesRegex(TimeoutError, 'already captured'):
                    camera.capture(SCAN_ROUTE[1], seen_centers=('red',), timeout_s=.15, settle_s=0)
            self.assertFalse(camera.thread.is_alive())
            device.release.assert_called_once()
        self.assertIs(getattr(vision2, 'camera_thread', None), owner)


class TestAutoWorkspace(unittest.TestCase):
    def setUp(self):
        """Input: hidden Tk. Output: real navigation and an independent automatic workspace."""
        self.root = tk.Tk()
        self.root.withdraw()
        canvas = tk.Canvas(self.root)
        canvas.pack()
        window = canvas.create_window(0, 0, window=tk.Button(canvas, text='Random'))
        self.client = SimpleNamespace(canvas=canvas, brandom_window=window,
                                      cancel_guidance=Mock(), pause_scan=Mock(), empty=Mock(),
                                      close_client=Mock(side_effect=self.root.destroy),
                                      vision2=SimpleNamespace(camera_stop=Event(), camera_options=None))
        self.old = ScrambleWorkspace(self.root, self.client)
        self.auto = AutoSolveWorkspace(self.root, self.client, self.old)
        self.addCleanup(self.cleanup)

    def cleanup(self):
        """Input: completed test. Output: destroy a still-open root once."""
        if not self.auto.closed:
            self.root.destroy()

    def pump(self, condition):
        """Input: completion predicate. Output: bounded Tk event processing."""
        end = time.monotonic()+3
        while not condition() and time.monotonic() < end:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(condition())

    def test_navigation_preserves_existing_scramble_model_and_guide_widgets(self):
        """Input: switching all three tabs. Output: retained scramble plan and original callbacks."""
        self.old.select_mode('scramble')
        self.old.generate()
        plan = self.old.plan
        self.old.select_mode('auto')
        self.assertEqual(self.old.mode, 'auto')
        self.assertEqual(self.old.frame.winfo_manager(), '')
        self.auto.events.put((0, 'face', cube_faces(SCRAMBLED)))
        self.pump(lambda: len(self.auto.faces) == 6)
        self.assertEqual(self.old.plan, plan)
        self.assertEqual(self.old.cube_state, plan.cube)
        self.old.select_mode('scramble')
        self.assertEqual(self.old.plan, plan)
        self.old.select_mode('guide')
        self.client.empty.assert_called_once()
        self.assertEqual(self.old.mode, 'guide')

    def test_start_locks_tabs_and_displays_completion(self):
        """Input: background automatic job. Output: six-face status and retained export after finish."""
        self.auto.select_mode('auto')
        self.auto.port.set('COM_TEST')
        release = Event()

        def run(settings, cancel, emit, preview):
            """Input: UI job snapshot. Output: delayed mocked scan/solve events."""
            release.wait(2)
            emit('face', cube_faces(SCRAMBLED))
            emit('scan_complete', '6/6 faces captured')
            emit('solution', {'cube': SCRAMBLED, 'solution': SOLUTION, 'uart': 'TURN D 2 900\n'})

        with patch('rubik_robot.auto_solve_panel.run_auto_solve', side_effect=run) as runner:
            self.auto.start()
            self.auto.start()
            self.old.select_mode('guide')
            self.assertEqual(self.old.mode, 'auto')
            release.set()
            self.pump(lambda: not self.auto.busy)
            runner.assert_called_once()
        self.assertIn('6/6', self.auto.scan_status.get())
        self.assertIn('complete', self.auto.status.get())
        self.assertEqual(self.auto.solution_frames, 'TURN D 2 900\n')
        self.auto.events.put((-1, 'face', {}))
        self.pump(self.auto.events.empty)
        self.assertEqual(len(self.auto.faces), 6)

    def test_preview_places_detected_center_at_machine_position(self):
        """Input: red up and blue front. Output: net displays those actual colors at U and F."""
        self.auto.select_mode('auto')
        self.auto.events.put((0, 'orientation', {'U': 'red', 'F': 'blue'}))
        self.auto.events.put((0, 'face', {'red': ('red',)*9, 'blue': ('blue',)*9}))
        self.pump(lambda: len(self.auto.faces) == 2)
        rectangles = [item for item in self.auto.net.find_all() if self.auto.net.type(item) == 'rectangle']
        fills = [self.auto.net.itemcget(item, 'fill') for item in rectangles]
        self.assertEqual(fills[:9], ['red']*9)
        self.assertEqual(fills[18:27], ['blue']*9)
        self.client.empty.assert_not_called()

    def test_close_waits_for_worker_cleanup(self):
        """Input: close during an automatic job. Output: cancellation before closing the root."""
        self.auto.select_mode('auto')
        self.auto.port.set('COM_TEST')
        release = Event()

        def run(settings, cancel, emit, preview):
            """Input: running job. Output: emulate resource cleanup after current operation."""
            release.wait(2)
            self.assertTrue(cancel.is_set())
            raise AutoSolveCancelled('Stopped')

        with patch('rubik_robot.auto_solve_panel.run_auto_solve', side_effect=run):
            self.auto.start()
            self.auto.close()
            self.client.close_client.assert_not_called()
            release.set()
            self.pump(lambda: self.client.close_client.called)
        self.assertTrue(self.auto.closed)


if __name__ == '__main__':
    unittest.main()
