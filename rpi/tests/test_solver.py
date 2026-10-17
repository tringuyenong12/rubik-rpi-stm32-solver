import unittest

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.solver.kociemba_solver import normalize_twophase_solution, solve_cube


class TestSolver(unittest.TestCase):
    def test_solve_solved_cube_returns_empty(self):
        self.assertEqual(solve_cube(SOLVED_CUBE), "")

    def test_normalize_twophase_solution(self):
        raw = "D2 L3 D3 L2 U1 R2 F1 (20f)"
        expected = "D2 L' D' L2 U R2 F"
        self.assertEqual(normalize_twophase_solution(raw), expected)

    def test_solve_scrambled_cube_with_twophase(self):
        scramble = "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL"
        solution = solve_cube(scramble)
        self.assertTrue(len(solution) > 0)
        # Verify tokens are standard moves
        for token in solution.split():
            self.assertIn(token[0], "URFDLB")


if __name__ == "__main__":
    unittest.main()
