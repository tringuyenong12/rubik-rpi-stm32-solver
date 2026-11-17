"""Keep valid scans usable when the optional local TCP service is absent."""
import unittest
from unittest.mock import MagicMock, patch

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.vision.solve_guide import apply_move, request_solution


class TestSolverConnection(unittest.TestCase):
    def test_loopback_refusal_uses_local_solver_and_verifies_solution(self):
        cube = apply_move(SOLVED_CUBE, 'R')
        for host in ('localhost', '127.0.0.1', '::1'):
            with self.subTest(host=host), \
                    patch('rubik_robot.vision.solve_guide.socket.create_connection', side_effect=ConnectionRefusedError), \
                    patch('rubik_robot.vision.solve_guide.solve_cube', return_value="R'") as local:
                self.assertEqual(request_solution(host, 8080, cube), "R'")
                local.assert_called_once_with(cube, max_length=20, timeout=3)

    def test_remote_refusal_does_not_silently_switch_solver(self):
        with patch('rubik_robot.vision.solve_guide.socket.create_connection', side_effect=ConnectionRefusedError), \
                patch('rubik_robot.vision.solve_guide.solve_cube') as local:
            with self.assertRaises(ConnectionRefusedError):
                request_solution('solver.example', 8080, SOLVED_CUBE)
            local.assert_not_called()

    def test_invalid_local_solution_cannot_start_guidance(self):
        with patch('rubik_robot.vision.solve_guide.socket.create_connection', side_effect=ConnectionRefusedError), \
                patch('rubik_robot.vision.solve_guide.solve_cube', return_value='U'):
            with self.assertRaises(ValueError):
                request_solution('localhost', 8080, apply_move(SOLVED_CUBE, 'R'))

    def test_already_solved_cube_accepts_empty_local_solution(self):
        with patch('rubik_robot.vision.solve_guide.socket.create_connection', side_effect=ConnectionRefusedError), \
                patch('rubik_robot.vision.solve_guide.solve_cube', return_value=''):
            self.assertEqual(request_solution('localhost', 8080, SOLVED_CUBE), '')

    def test_available_tcp_server_keeps_existing_protocol(self):
        connection = MagicMock()
        connection.__enter__.return_value.makefile.return_value.__enter__.return_value.readline.return_value = 'R3 (1f)\n'
        cube = apply_move(SOLVED_CUBE, 'R')
        with patch('rubik_robot.vision.solve_guide.socket.create_connection', return_value=connection), \
                patch('rubik_robot.vision.solve_guide.solve_cube') as local:
            self.assertEqual(request_solution('localhost', 8080, cube), "R'")
            connection.__enter__.return_value.sendall.assert_called_once_with((cube+'\n').encode('ascii'))
            local.assert_not_called()


if __name__ == '__main__':
    unittest.main()
