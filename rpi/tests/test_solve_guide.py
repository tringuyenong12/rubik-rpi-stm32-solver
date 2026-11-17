"""Exercise complete six-face recovery and camera-confirmed arrow guidance."""

from itertools import permutations
import unittest
from unittest.mock import patch
import importlib
import threading
import time
import tkinter

import numpy as np
import cv2
from unittest.mock import Mock

from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE
from rubik_robot.vision.face_scanner import COLORS, FaceScanner
from rubik_robot.vision.solve_guide import (
    SolveGuide, apply_move, cube_faces, face_definition, minimum_assignment,
    prepare_cube, rotate_grid, turn_paths, valid_cube, view_paths, changed_view_rotation,
)


SCRAMBLED = 'DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL'
PROTOTYPES = ((30, 230, 220), (60, 220, 190), (1, 230, 210),
              (0, 10, 220), (115, 230, 200), (17, 230, 230))


class TestScanRecovery(unittest.TestCase):
    def test_complete_scan_recovers_misclassified_colors_from_centers(self):
        """Input: excess red labels and true HSV samples. Output: the original valid cube."""
        faces = cube_faces(SCRAMBLED)
        samples = {color: tuple(PROTOTYPES[COLORS.index(value)] for value in faces[color]) for color in COLORS}
        damaged = {color: list(values) for color, values in faces.items()}
        changed = 0
        for values in damaged.values():
            for index, value in enumerate(values):
                if index != 4 and value == 'orange':
                    values[index] = 'red'
                    changed += 1
        cube, recovered, centers, note = prepare_cube(damaged, samples)
        self.assertEqual(cube, SCRAMBLED)
        self.assertEqual(recovered, faces)
        self.assertEqual(centers.shape, (6, 3))
        self.assertIn(f'{changed} stickers', note)

    def test_face_directions_are_recovered_only_when_unique(self):
        """Input: rotated scan grids. Output: the unique physically valid definition."""
        faces = cube_faces(SCRAMBLED)
        rotated = {color: rotate_grid(faces[color], index % 4) for index, color in enumerate(COLORS)}
        self.assertEqual(prepare_cube(rotated)[0], SCRAMBLED)

    def test_invalid_scan_remains_available_for_rescan(self):
        """Input: six faces with a wrong count. Output: retain six faces and report validation."""
        scanner = FaceScanner(stable_seconds=0, min_samples=1)
        faces = cube_faces(SCRAMBLED)
        for color, values in faces.items():
            values = list(values)
            if color == 'orange':
                values[0] = 'red' if values[0] != 'red' else 'white'
            scanner.update([values[:3], values[3:6], values[6:]], now=COLORS.index(color))
        self.assertEqual(len(scanner.snapshot()['faces']), 6)
        with self.assertRaises(ValueError):
            prepare_cube(scanner.snapshot()['faces'])
        scanner.forget('orange')
        self.assertEqual(len(scanner.snapshot()['faces']), 5)

    def test_assignment_is_minimum_cost_and_uses_each_slot_once(self):
        """Input: square costs. Output: an optimal one-to-one assignment."""
        costs = np.asarray([[9., 2., 4.], [6., 5., 3.], [5., 1., 8.]])
        assigned = minimum_assignment(costs)
        expected = min(sum(costs[row, col] for row, col in enumerate(order)) for order in permutations(range(3)))
        self.assertEqual(len(set(assigned)), 3)
        self.assertEqual(sum(costs[np.arange(3), assigned]), expected)

    def test_circular_hue_samples_survive_saving_and_rotation(self):
        """Input: red samples around hue wrap. Output: saved hue near zero and rotated samples."""
        scanner = FaceScanner(stable_seconds=0.18, min_samples=4)
        for index, hue in enumerate((179, 1, 179, 1)):
            samples = [[[hue, 220, 210] for _ in range(3)] for _ in range(3)]
            scanner.update([['red'] * 3 for _ in range(3)], index*.07, samples)
        values = scanner.snapshot()['hsv_faces']['red']
        self.assertTrue(values[0][0] < 3 or values[0][0] > 177)
        scanner.rotate('red')
        self.assertEqual(len(scanner.snapshot()['hsv_faces']['red']), 9)


class TestSolveGuide(unittest.TestCase):
    def show(self, session, cube, now, rotation=0):
        """Input: actual cube and requested view. Output: five stable camera observations."""
        color = COLORS[FACE_ORDER.index(session.snapshot()['view'])]
        values = rotate_grid(cube_faces(cube)[color], rotation)
        for _ in range(5):
            now += .07
            session.observe([values[:3], values[3:6], values[6:]], now)
        return now

    def finish(self, session, actual_cube):
        """Input: guide and actual initial cube. Output: simulated physical cube at completion."""
        now, last_turned = 0, -1
        for _ in range(300):
            state = session.snapshot()
            if state['phase'] == 'solved':
                return actual_cube
            if state['phase'] == 'turn' and state['index'] != last_turned:
                actual_cube = apply_move(actual_cube, session.moves[state['index']])
                last_turned = state['index']
            now = self.show(session, actual_cube, now)
        self.fail(f'Guide stalled: {session.snapshot()}')

    def test_all_eighteen_moves_reach_solved_after_camera_confirmation(self):
        """Input: each standard move from solved. Output: guided inverse solves the actual cube."""
        inverses = {'': "'", "'": '', '2': '2'}
        for face in FACE_ORDER:
            for suffix, inverse in inverses.items():
                with self.subTest(move=face+suffix):
                    cube = apply_move(SOLVED_CUBE, face+suffix)
                    session = SolveGuide()
                    session.begin(cube, face+inverse)
                    self.assertEqual(self.finish(session, cube), SOLVED_CUBE)
                    self.assertEqual(session.snapshot()['message'], 'CUBE SOLVED!')

    def test_long_solution_updates_the_cube_after_every_confirmed_step(self):
        """Input: a multi-face scramble. Output: verified model and actual cube both solve."""
        scramble = ['R', 'U', 'F2', "L'", 'D', 'B']
        cube = SOLVED_CUBE
        for move in scramble:
            cube = apply_move(cube, move)
        inverse = ' '.join(move if move.endswith('2') else move[0] if move.endswith("'") else move+"'"
                           for move in reversed(scramble))
        session = SolveGuide()
        session.begin(cube, inverse)
        self.assertEqual(self.finish(session, cube), SOLVED_CUBE)
        self.assertEqual(session.snapshot()['cube'], SOLVED_CUBE)

    def test_wrong_turn_or_incomplete_detection_does_not_advance(self):
        """Input: wrong physical turn and missing grid. Output: retain the current step."""
        cube = apply_move(SOLVED_CUBE, 'R')
        session = SolveGuide()
        session.begin(cube, "R'")
        now = self.show(session, cube, 0)
        self.assertEqual(session.snapshot()['phase'], 'turn')
        wrong = apply_move(cube, 'L')
        self.show(session, wrong, now)
        session.observe([], 5)
        self.assertEqual(session.snapshot()['index'], 0)
        self.assertNotEqual(session.snapshot()['phase'], 'solved')

    def test_ambiguous_turn_waits_for_an_additional_face(self):
        """Input: a turn with an ambiguous primary view. Output: require a second face before commit."""
        cube = 'BUDFURUDFDDRLRDFULFLLRFBLFRBLUBDBDUBRRLLLBBDUFFUFBUDRR'
        solution = "B F U2 F' R' U' F' R' B' R L F2 R2 F2 R2 L2 U2 B2 L2 B R2"
        session = SolveGuide()
        session.begin(cube, solution)
        self.assertTrue(session.witnesses)
        now = self.show(session, cube, 0)
        after = apply_move(cube, 'B')
        now = self.show(session, after, now)
        self.assertEqual(session.snapshot()['phase'], 'verify')
        self.assertEqual(session.snapshot()['cube'], cube)
        now = self.show(session, cube, now)
        self.assertEqual(session.snapshot()['index'], 0)
        self.show(session, after, now)
        self.assertEqual(session.snapshot()['index'], 1)
        self.assertEqual(session.snapshot()['cube'], after)

    def test_rotated_camera_view_produces_rotated_arrows(self):
        """Input: a face rotated in the camera. Output: arrows follow its image orientation."""
        cube = apply_move(SOLVED_CUBE, 'R')
        session = SolveGuide()
        session.begin(cube, "R'")
        self.show(session, cube, 0, rotation=1)
        state = session.snapshot()
        self.assertEqual(state['rotation'], 1)
        self.assertEqual(state['phase'], 'turn')
        self.assertTrue(state['paths'])

    def test_one_missed_frame_does_not_stall_a_correct_turn(self):
        """Input: one missed detection during a correct turn. Output: confirm using four good frames."""
        cube = apply_move(SOLVED_CUBE, 'R')
        session = SolveGuide()
        session.begin(cube, "R'")
        now = self.show(session, cube, 0)
        values = cube_faces(SOLVED_CUBE)['red']
        for index in range(5):
            now += .07
            grid = [] if index == 2 else [values[:3], values[3:6], values[6:]]
            session.observe(grid, now)
        self.assertEqual(session.snapshot()['phase'], 'solved')

    def test_invalid_server_solution_is_rejected(self):
        """Input: moves that leave the cube scrambled. Output: reject guidance."""
        session = SolveGuide()
        with self.assertRaises(ValueError):
            session.begin(apply_move(SOLVED_CUBE, 'R'), 'U')
        self.assertEqual(session.snapshot()['phase'], 'idle')

    def test_reset_cancels_guidance_and_solved_scan_is_immediate(self):
        """Input: solved scan then reset. Output: solved banner followed by idle scan state."""
        session = SolveGuide()
        session.begin(SOLVED_CUBE, '')
        self.assertEqual(session.snapshot()['phase'], 'solved')
        session.reset()
        self.assertEqual(session.snapshot()['phase'], 'idle')
        self.assertEqual(session.snapshot()['cube'], '')


class TestArrowGeometry(unittest.TestCase):
    def test_whole_cube_changes_preserve_camera_roll(self):
        """Input: adjacent view transitions. Output: roll consistent with the cube's 3D axes."""
        self.assertEqual(changed_view_rotation(2, 1, 0), 0)
        self.assertEqual(changed_view_rotation(2, 0, 0), 0)
        self.assertEqual(changed_view_rotation(0, 1, 0), 3)
    def test_face_turn_directions_match_standard_cube_axes(self):
        """Input: adjacent-face moves. Output: arrows point along their physical strip motion."""
        for move, axis, sign in (('R', 1, -1), ("R'", 1, 1), ('L', 1, 1), ('U', 0, -1), ('D', 0, 1)):
            with self.subTest(move=move):
                path = turn_paths('F', move)[0]
                self.assertEqual(np.sign(path[1, axis]-path[0, axis]), sign)

    def test_whole_cube_reorientation_draws_three_parallel_arrows(self):
        """Input: front-to-right view change. Output: three left-pointing whole-cube arrows."""
        paths = view_paths('F', 'R')
        self.assertEqual(len(paths), 3)
        self.assertTrue(all(path[1, 0] < path[0, 0] for path in paths))

    def test_camera_loop_confirms_a_real_rendered_turn_and_draws_solved(self):
        """Input: generated before/after camera frames. Output: camera-driven solved session."""
        from twophase import vision2
        cube = apply_move(SOLVED_CUBE, 'R')
        session = SolveGuide()
        session.begin(cube, "R'")
        palette = {'yellow': (0, 255, 255), 'green': (0, 220, 0), 'red': (0, 0, 230),
                   'white': (230, 230, 230), 'blue': (230, 0, 0), 'orange': (0, 165, 255)}
        frames = []
        for definition in (cube, SOLVED_CUBE):
            frame = np.full((480, 640, 3), 20, dtype=np.uint8)
            for index, color in enumerate(cube_faces(definition)['red']):
                x, y = 210 + index % 3 * 65, 140 + index // 3 * 65
                cv2.rectangle(frame, (x, y), (x+50, y+50), palette[color], -1)
            frames.extend([frame.copy() for _ in range(6)])
        capture = Mock()
        capture.isOpened.return_value = True
        capture.read.side_effect = [(True, frame) for frame in frames]
        scanner = FaceScanner()
        scanner.set_enabled(False)
        with patch.object(vision2, 'scanner', scanner), patch.object(vision2, 'guide', session), \
                patch.object(cv2, 'VideoCapture', return_value=capture), \
                patch.object(cv2, 'imshow') as show, patch.object(cv2, 'destroyAllWindows'), \
                patch.object(cv2, 'moveWindow'), patch.object(cv2, 'getWindowProperty', return_value=1), \
                patch.object(cv2, 'waitKey', side_effect=[-1]*11+[ord('x')]), \
                patch('rubik_robot.vision.solve_guide.monotonic', side_effect=np.arange(12)*.07):
            vision2.grab_colors(1, cv2.CAP_DSHOW, show_masks=False)
        self.assertEqual(session.snapshot()['phase'], 'solved')
        self.assertEqual(session.snapshot()['cube'], SOLVED_CUBE)
        self.assertEqual(len(show.call_args_list), 12)
        self.assertTrue(all(call.args[0] == 'Rubik Cube Detection' for call in show.call_args_list))


class TestDesktopFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Input: Tk runtime. Output: a hidden real editor with the event loop controlled by tests."""
        original = tkinter.Tk.__init__

        def hidden_init(root, *args, **kwargs):
            """Input: Tk constructor arguments. Output: initialized hidden root."""
            original(root, *args, **kwargs)
            root.withdraw()

        try:
            with patch.object(tkinter.Tk, '__init__', hidden_init), patch.object(tkinter.Tk, 'mainloop'):
                cls.gui = importlib.import_module('twophase.client_gui2')
        except tkinter.TclError as error:
            raise unittest.SkipTest(f'Tk display unavailable: {error}')

    @classmethod
    def tearDownClass(cls):
        """Input: test editor. Output: close Tk and cancel pending guidance."""
        cls.gui.close_client()

    def setUp(self):
        """Input: previous editor state. Output: a fresh scan with automatic guidance enabled."""
        self.gui.empty()
        self.gui.auto_guide.set(True)
        self.gui.display.delete('1.0', 'end')

    def populate(self, cube):
        """Input: physical cube. Output: stable six-face camera capture in the live scanner."""
        for index, (color, values) in enumerate(cube_faces(cube).items()):
            for step in range(5):
                self.gui.scanner.update([values[:3], values[3:6], values[6:]], index + step*.07)
        self.gui.refresh_scan()

    def wait_for(self, condition):
        """Input: completion predicate. Output: pump Tk until completion or a bounded failure."""
        deadline = time.monotonic() + 4
        while not condition() and time.monotonic() < deadline:
            self.gui.root.update()
            time.sleep(.01)
        self.assertTrue(condition())

    def test_six_faces_automatically_request_solution_and_update_editor(self):
        """Input: sixth captured face. Output: start guidance and render confirmed cube updates."""
        cube = apply_move(SOLVED_CUBE, 'R')
        self.populate(cube)
        with patch.object(self.gui, 'request_solution', return_value="R'") as request:
            self.gui.poll_scan()
            self.wait_for(lambda: self.gui.guide.snapshot()['phase'] == 'align')
            request.assert_called_once_with('localhost', 8080, cube)
        self.assertEqual(self.gui.get_definition_string(), cube)
        helper = TestSolveGuide()
        self.assertEqual(helper.finish(self.gui.guide, cube), SOLVED_CUBE)
        self.gui.refresh_scan()
        self.assertEqual(self.gui.get_definition_string(), SOLVED_CUBE)
        self.assertEqual(self.gui.scan_status.get(), 'CUBE SOLVED!')

    def test_server_error_keeps_camera_state_and_rescan_controls_available(self):
        """Input: unavailable server. Output: retain all six faces and permit correction/retry."""
        self.populate(apply_move(SOLVED_CUBE, 'R'))
        with patch.object(self.gui, 'request_solution', side_effect=OSError('Server unavailable')):
            self.gui.poll_scan()
            self.wait_for(lambda: self.gui.guide.snapshot()['phase'] == 'error')
        self.assertFalse(self.gui.solving)
        self.assertEqual(len(self.gui.scanner.snapshot()['faces']), 6)
        self.assertEqual(str(self.gui.rescan_button['state']), 'normal')
        self.gui.rescan_current()
        self.assertEqual(len(self.gui.scanner.snapshot()['faces']), 5)

    def test_bad_color_counts_show_all_six_faces_and_correction_borders(self):
        """Input: an invalid sixth-face label. Output: retain it, highlight conflicts and permit retry."""
        self.populate(SCRAMBLED)
        old = self.gui.scanner.snapshot()['faces']['orange'][0]
        self.gui.scanner.edit('orange', 0, 'white' if old != 'white' else 'red')
        with patch.object(self.gui, 'request_solution') as request:
            self.gui.poll_scan()
            self.wait_for(lambda: self.gui.guide.snapshot()['phase'] == 'error')
            request.assert_not_called()
        self.assertEqual(len(self.gui.scanner.snapshot()['faces']), 6)
        self.assertIn('9', self.gui.scan_status.get())
        outlines = [self.gui.canvas.itemcget(sticker, 'outline')
                    for face in self.gui.facelet_id for row in face for sticker in row]
        self.assertIn('darkorange', outlines)

    def test_new_scan_discards_an_old_server_reply(self):
        """Input: New scan during a pending request. Output: ignore its late solution."""
        self.populate(apply_move(SOLVED_CUBE, 'R'))
        started, release = threading.Event(), threading.Event()

        def delayed_reply(*args):
            """Input: solver request. Output: a deliberately delayed valid solution."""
            started.set()
            release.wait(3)
            return "R'"

        with patch.object(self.gui, 'request_solution', side_effect=delayed_reply):
            self.gui.solve()
            self.assertTrue(started.wait(2))
            self.gui.empty()
            release.set()
            self.wait_for(lambda: not self.gui.solve_results.empty())
            self.gui.receive_solution()
        self.assertEqual(self.gui.guide.snapshot()['phase'], 'idle')
        self.assertEqual(self.gui.scanner.snapshot()['faces'], {})
        self.assertFalse(self.gui.solving)


if __name__ == '__main__':
    unittest.main()
