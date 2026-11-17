"""Verify level generation, complete UART handshakes and independent mode navigation."""

from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
import time
import tkinter as tk
import unittest
from unittest.mock import Mock, patch

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.protocol import Command
from rubik_robot.scramble import AXES, LEVELS, create_scramble
from rubik_robot.scramble_panel import FACE_COLORS, LEVEL_LABELS, ScrambleWorkspace
from rubik_robot.transport.scramble_sender import ScrambleSendError, SendResult, send_scramble
from rubik_robot.transport.serial_link import SerialLink
from rubik_robot.vision.solve_guide import apply_move, valid_cube


class FakeSerial:
    """In-memory device implementing PING, ACK and DONE without moving hardware."""

    def __init__(self, fail_at=None, ack_only=False, partial=False):
        """Input: simulated failure options. Output: an unopened-command fake device."""
        self.timeout = 10
        self.lines = deque([b'OK BOOT\n', b'DONE TURN\n'])
        self.writes = []
        self.turns = 0
        self.fail_at, self.ack_only, self.partial = fail_at, ack_only, partial
        self.closed = False

    def write(self, frame):
        """Input: UART bytes. Output: queue protocol responses and record the frame."""
        self.writes.append(frame)
        if frame == b'PING\n':
            self.lines.append(b'OK PONG\n')
        else:
            self.turns += 1
            if self.turns == self.fail_at:
                self.lines.append(b'ERR UNSUPPORTED move_sequence\n')
            elif self.ack_only:
                self.lines.append(b'OK TURN\n')
            elif self.partial:
                self.lines.extend((b'OK TU', b'RN\r\nDO', b'NE TURN\r\n'))
            else:
                self.lines.extend((b'OK TURN\n', b'DONE TURN\n'))

    def flush(self):
        """Input: none. Output: writes are already available to the fake device."""

    def readline(self):
        """Input: none. Output: next complete/partial device response."""
        return self.lines.popleft() if self.lines else b''

    def close(self):
        """Input: none. Output: mark the serial connection closed."""
        self.closed = True


class TestScramblePlan(unittest.TestCase):
    def test_levels_generate_valid_states_and_matching_uart_moves(self):
        """Input: three levels and varied seeds. Output: legal target states from solved."""
        for level, length in LEVELS.items():
            for seed in range(20):
                with self.subTest(level=level, seed=seed):
                    plan = create_scramble(level, seed)
                    self.assertEqual(len(plan.moves), length)
                    self.assertEqual(len(plan.actions), length)
                    cube = SOLVED_CUBE
                    for move in plan.moves:
                        cube = apply_move(cube, move)
                    self.assertEqual(plan.cube, cube)
                    self.assertTrue(valid_cube(plan.cube))
                    self.assertNotEqual(plan.cube, SOLVED_CUBE)
                    self.assertTrue(all(AXES[a[0]] != AXES[b[0]] for a, b in zip(plan.moves, plan.moves[1:])))
                    self.assertEqual(plan.uart_text().count('\n'), length)

    def test_repeated_seed_and_duration_export(self):
        """Input: fixed seed/command timing. Output: reproducible moves and correct 180-degree timing."""
        first = create_scramble('hard', 9, duration_ms=100, command_name='MOVE')
        self.assertEqual(first, create_scramble('hard', 9, duration_ms=100, command_name='MOVE'))
        for move, action in zip(first.moves, first.actions):
            self.assertEqual(action.command.name, 'MOVE')
            self.assertEqual(action.command.duration_ms, 200 if move.endswith('2') else 100)

    def test_invalid_settings_are_rejected(self):
        """Input: unsupported level or nonpositive duration. Output: explicit input errors."""
        with self.assertRaises(ValueError):
            create_scramble('expert')
        with self.assertRaises(ValueError):
            create_scramble('easy', duration_ms=0)


class TestScrambleUART(unittest.TestCase):
    def test_ordered_transmission_waits_for_done_and_handles_partial_lines(self):
        """Input: split UART responses. Output: all turns completed in exported order."""
        plan = create_scramble('easy', 7)
        serial = FakeSerial(partial=True)
        progress = []
        with patch('serial.Serial', return_value=serial), patch('rubik_robot.transport.serial_link.time.sleep'):
            result = send_scramble(plan, 'COM_TEST', progress=lambda count, reply: progress.append(count))
        self.assertEqual(result, SendResult(5, False))
        self.assertEqual(serial.writes, [b'PING\n'] + [line.encode() + b'\n' for line in plan.uart_text().splitlines()])
        self.assertEqual(progress, [1, 2, 3, 4, 5])
        self.assertTrue(serial.closed)

    def test_error_stops_without_retrying_a_turn(self):
        """Input: firmware error on third move. Output: two completed moves and no automatic retry."""
        serial = FakeSerial(fail_at=3)
        with patch('serial.Serial', return_value=serial), patch('rubik_robot.transport.serial_link.time.sleep'):
            with self.assertRaises(ScrambleSendError) as caught:
                send_scramble(create_scramble('easy', 1), 'COM_TEST')
        self.assertEqual(caught.exception.completed, 2)
        self.assertTrue(caught.exception.uncertain_move)
        self.assertEqual(serial.turns, 3)
        self.assertTrue(serial.closed)

    def test_ack_without_done_is_not_counted_as_completed(self):
        """Input: ACK without completion. Output: timeout before another move is sent."""
        serial = FakeSerial(ack_only=True)
        with patch('serial.Serial', return_value=serial), patch('rubik_robot.transport.serial_link.time.sleep'):
            with self.assertRaises(ScrambleSendError) as caught:
                send_scramble(create_scramble('easy', 1), 'COM_TEST', timeout_s=.01)
        self.assertEqual(caught.exception.completed, 0)
        self.assertEqual(serial.turns, 1)

    def test_cancellation_stops_after_the_completed_turn(self):
        """Input: stop after two moves. Output: remaining turns stay unsent."""
        serial = FakeSerial()
        cancel = Event()

        def progress(count, reply):
            """Input: completion count. Output: request cancellation at move two."""
            if count == 2:
                cancel.set()

        with patch('serial.Serial', return_value=serial), patch('rubik_robot.transport.serial_link.time.sleep'):
            result = send_scramble(create_scramble('easy', 1), 'COM_TEST', cancel=cancel, progress=progress)
        self.assertEqual(result, SendResult(2, True))
        self.assertEqual(serial.turns, 2)

    def test_pre_cancelled_send_does_not_open_a_port(self):
        """Input: cancelled job. Output: zero serial traffic."""
        cancel = Event()
        cancel.set()
        with patch('serial.Serial') as serial:
            self.assertEqual(send_scramble(create_scramble('easy'), 'COM_TEST', cancel=cancel), SendResult(0, True))
        serial.assert_not_called()

    def test_stale_done_before_ack_is_ignored(self):
        """Input: old DONE followed only by new ACK. Output: wait for the new completion."""
        link = SerialLink('COM_TEST', timeout_s=.01)
        serial = FakeSerial(ack_only=True)
        link._serial = serial
        with self.assertRaises(TimeoutError):
            link.request_completed(Command('TURN', ('R', 1, 450)))
        self.assertEqual(serial.timeout, 10)


class TestScrambleWorkspace(unittest.TestCase):
    def setUp(self):
        """Input: Tk runtime. Output: isolated workspace and untouched guide callback stubs."""
        try:
            self.root = tk.Tk()
        except tk.TclError as error:
            self.skipTest(str(error))
        self.root.withdraw()
        canvas = tk.Canvas(self.root)
        canvas.pack()
        button = tk.Button(self.root, text='Random')
        button_window = canvas.create_window(10, 10, window=button, anchor=tk.NW)
        self.client = SimpleNamespace(canvas=canvas, brandom=button, brandom_window=button_window, cancel_guidance=Mock(),
                                      pause_scan=Mock(), empty=Mock(), close_client=Mock(side_effect=self.root.destroy),
                                      vision2=SimpleNamespace(camera_stop=Event(), camera_options=None))
        self.port_patch = patch('rubik_robot.scramble_panel.list_ports.comports', return_value=[SimpleNamespace(device='COM_TEST')])
        self.port_patch.start()
        self.addCleanup(self.port_patch.stop)
        self.workspace = ScrambleWorkspace(self.root, self.client)

    def tearDown(self):
        """Input: test workspace. Output: close its root and queued callbacks."""
        if hasattr(self, 'workspace') and not self.workspace.closed:
            self.workspace.close()

    def wait_for(self, condition):
        """Input: worker completion predicate. Output: pump Tk with a bounded wait."""
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.01)
        self.assertTrue(condition())

    def test_default_guide_mount_and_mode_switch(self):
        """Input: mounting and selecting modes. Output: guide callbacks run only on navigation."""
        self.client.cancel_guidance.assert_not_called()
        self.client.empty.assert_not_called()
        self.workspace.select_mode('scramble')
        self.assertEqual(self.client.canvas.winfo_manager(), '')
        self.assertTrue(self.client.vision2.camera_stop.is_set())
        self.workspace.select_mode('guide')
        self.assertEqual(self.client.canvas.winfo_manager(), 'pack')
        self.client.empty.assert_called_once()
        self.assertEqual(self.client.canvas.itemcget(self.client.brandom_window, 'state'), 'hidden')
        self.assertEqual(self.workspace.scramble_button['text'], 'Scramble')

    def test_levels_export_the_displayed_plan(self):
        """Input: difficulty choices. Output: exact matching UART frames in text, clipboard and file."""
        for label, level in LEVEL_LABELS.items():
            self.workspace.level.set(label)
            self.workspace.generate()
            self.assertEqual(len(self.workspace.plan.moves), LEVELS[level])
            self.assertIn(self.workspace.plan.uart_text(), self.workspace.output.get('1.0', 'end'))
            self.assertEqual(self.workspace.cube_state, self.workspace.plan.cube)
            self.assertEqual(len(self.workspace.cube_stickers), 54)
            colors = [self.workspace.cube_canvas.itemcget(item, 'fill') for item in self.workspace.cube_stickers]
            self.assertEqual(colors, [FACE_COLORS[face] for face in self.workspace.plan.cube])
        self.workspace.copy()
        self.assertEqual(self.root.clipboard_get(), self.workspace.plan.uart_text())
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'scramble.txt'
            with patch('rubik_robot.scramble_panel.filedialog.asksaveasfilename', return_value=str(output)):
                self.workspace.save()
            self.assertEqual(output.read_bytes(), self.workspace.plan.uart_text().encode())

    def test_preview_starts_solved_and_is_isolated_from_the_guide(self):
        """Input: generating a target. Output: update only the scramble preview canvas."""
        self.assertEqual(self.workspace.cube_state, SOLVED_CUBE)
        guide_items = self.client.canvas.find_all()
        self.workspace.generate()
        self.assertEqual(self.client.canvas.find_all(), guide_items)
        self.client.cancel_guidance.assert_not_called()
        self.client.empty.assert_not_called()
        self.assertEqual(self.workspace.preview_title.get(), 'Target cube after scramble')

    def test_background_send_locks_navigation_and_reports_completion(self):
        """Input: pending UART job. Output: lock duplicate sends and release controls after completion."""
        self.workspace.select_mode('scramble')
        self.workspace.generate()
        release = Event()

        def send(plan, port, baud, cancel, progress):
            """Input: fixed job snapshot. Output: simulated completed send after release."""
            release.wait(2)
            progress(len(plan.moves), 'DONE TURN')
            return SendResult(len(plan.moves), False)

        with patch('rubik_robot.scramble_panel.send_scramble', side_effect=send) as sender:
            self.workspace.send()
            self.workspace.send()
            self.workspace.select_mode('guide')
            self.assertEqual(self.workspace.mode, 'scramble')
            release.set()
            self.wait_for(lambda: not self.workspace.busy)
            sender.assert_called_once()
        self.assertEqual(self.workspace.progress['value'], 5)
        self.assertIn('5/5', self.workspace.status.get())

    def test_close_waits_for_the_inflight_send_to_finish(self):
        """Input: close during a serial turn. Output: request cancellation and close after completion."""
        self.workspace.select_mode('scramble')
        self.workspace.generate()
        release = Event()

        def send(plan, port, baud, cancel, progress):
            """Input: current send. Output: finish its turn before reporting cancellation."""
            release.wait(2)
            return SendResult(1, cancel.is_set())

        with patch('rubik_robot.scramble_panel.send_scramble', side_effect=send):
            self.workspace.send()
            self.workspace.close()
            self.assertTrue(self.workspace.cancel.is_set())
            self.client.close_client.assert_not_called()
            release.set()
            self.wait_for(lambda: self.workspace.closed)
        self.client.close_client.assert_called_once()

    def test_camera_restart_waits_for_the_previous_owner(self):
        """Input: mode switch with camera still closing. Output: restart only after it releases."""
        old_owner = Mock()
        old_owner.is_alive.return_value = True
        vision = self.client.vision2
        vision.camera_thread = old_owner
        vision.camera_options = (1, 700, False)
        vision.grab_colors = Mock()
        new_owner = Mock()
        self.workspace.select_mode('scramble')
        with patch('rubik_robot.scramble_panel.Thread', return_value=new_owner) as create_thread:
            self.workspace.select_mode('guide')
            create_thread.assert_not_called()
            old_owner.is_alive.return_value = False
            self.wait_for(lambda: new_owner.start.called)
            create_thread.assert_called_once_with(target=vision.grab_colors, args=(1, 700, False), daemon=True)


if __name__ == '__main__':
    unittest.main()
