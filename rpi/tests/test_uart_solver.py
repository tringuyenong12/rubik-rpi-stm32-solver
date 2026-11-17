"""Exercise the real solver-to-motion-to-UART path without a serial device."""
from collections import deque
from threading import Event
import unittest
from unittest.mock import patch

from Rubik_Cube.UART_Command.session import UARTSession
from Rubik_Cube.motion import motion
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.protocol import Command, MoveCommand
from rubik_robot.transport.serial_link import SerialLink, MoveExecutionError
from rubik_robot.transport.scramble_sender import send_actions, ScrambleSendError
from rubik_robot.solver.execution import solution_plan, send_solution
from rubik_robot.cube.state import SOLVED_CUBE
from twophase.cubie import CubieCube, basicMoveCube


class Device:
    def __init__(self, fail_at=None, missing=None):
        self.writes = []
        self.lines = deque()
        self.fail_at, self.missing = fail_at, missing
        self.timeout = .1
        self.closed = False

    def write(self, frame):
        self.writes.append(frame)
        ident = frame.split()[0]
        prefix = b'>' + ident
        # Stale and debug responses must not complete this transaction.
        self.lines.extend((b'debug\n', b'>#999 DONE\n'))
        if len(self.writes) == self.fail_at:
            self.lines.append(prefix + b' ERR BAD_RUBIK_MOVE_ARG\n')
        else:
            if self.missing != 'OK':
                self.lines.extend((prefix + b' O', b'K\r\n'))
            if self.missing != 'DONE':
                self.lines.extend((prefix + b' DO', b'NE\r\n'))
        return len(frame)

    def flush(self):
        pass

    def readline(self):
        return self.lines.popleft() if self.lines else b''

    def close(self):
        self.closed = True


class TestUARTSolver(unittest.TestCase):
    def test_sessions_cannot_open_the_same_port_concurrently(self):
        device = Device()
        with patch('serial.Serial', return_value=device), SerialLink('COM_TEST') as first:
            with self.assertRaises(RuntimeError):
                UARTSession('COM_TEST').open()
        self.assertTrue(device.closed)

    def test_formula_calls_face_helpers_and_waits_for_each_half_turn(self):
        device = Device()
        actions = MotionPlanner().plan("R U' F2")
        with patch('serial.Serial', return_value=device), \
             patch.object(motion, 'move_R', wraps=motion.move_R) as right, \
             patch.object(motion, 'move_F', wraps=motion.move_F) as front:
            result = send_actions(actions, 'COM_TEST')
        self.assertEqual(result.completed, 3)
        self.assertEqual(right.call_count, 1)
        self.assertEqual(front.call_count, 2)
        self.assertEqual(device.writes, [b'#1 RUBIK PING\n', b'#2 RUBIK MOVE R\n',
                                       b'#3 RUBIK MOVE U_\n', b'#4 RUBIK MOVE F\n',
                                       b'#5 RUBIK MOVE F\n'])
        self.assertTrue(device.closed)

    def test_failure_in_second_half_preserves_partial_progress(self):
        device = Device(fail_at=3)  # PING, first F, second F fails.
        with patch('serial.Serial', return_value=device):
            with self.assertRaises(ScrambleSendError) as caught:
                send_actions(MotionPlanner().plan('F2 R'), 'COM_TEST')
        self.assertEqual(caught.exception.completed, 0)
        self.assertEqual(caught.exception.completed_quarter_turns, 1)
        self.assertTrue(caught.exception.uncertain_move)
        self.assertEqual(len(device.writes), 3)

    def test_missing_ack_or_done_times_out_without_retry(self):
        for missing in ('OK', 'DONE'):
            with self.subTest(missing=missing):
                device = Device(missing=missing)
                with patch('serial.Serial', return_value=device), SerialLink('COM_TEST', timeout_s=.005) as link:
                    with self.assertRaises(MoveExecutionError):
                        link.request_completed(MoveCommand('F', 1))
                    with self.assertRaises(RuntimeError):
                        link.request_completed(Command('PING'))
                self.assertEqual(len(device.writes), 1)

    def test_invalid_or_unsupported_command_does_not_write(self):
        device = Device()
        with patch('serial.Serial', return_value=device), SerialLink('COM_TEST') as link:
            for command in (Command('SCAN_POSE', ('F',)), Command('STOP'), Command('HOME')):
                with self.assertRaises(ValueError):
                    link.request_completed(command)
            with self.assertRaises(NotImplementedError):
                link.require_scan_support()
            with self.assertRaises(ValueError):
                link.session.request('RUBIK MOVE F\nRUBIK MOVE R')
            link.session.command_id = 65535
            with self.assertRaises(RuntimeError):
                link.request_completed(Command('PING'))
        self.assertFalse(device.writes)

    def test_verified_solution_and_rejected_wrong_solution(self):
        cube = CubieCube()
        cube.multiply(basicMoveCube['URFDLB'.index('F')])
        state = cube.to_facelet_cube().to_string()
        _, actions = solution_plan(state, 'F3')
        self.assertEqual(actions[0].to_wire(), 'RUBIK MOVE F_')
        device = Device()
        with patch('serial.Serial', return_value=device):
            self.assertEqual(send_solution(state, 'COM_TEST', solution="F'").completed, 1)
        with patch('serial.Serial') as serial:
            with self.assertRaises(ValueError):
                send_solution(state, 'COM_TEST', solution='R')
            serial.assert_not_called()

    def test_cancel_and_solved_cube_do_not_open_uart(self):
        cancel = Event()
        cancel.set()
        with patch('serial.Serial') as serial:
            result = send_actions(MotionPlanner().plan('F'), 'COM_TEST', cancel=cancel)
            self.assertTrue(result.cancelled)
            self.assertEqual(send_solution(SOLVED_CUBE, 'COM_TEST').completed, 0)
            serial.assert_not_called()


if __name__ == '__main__':
    unittest.main()
