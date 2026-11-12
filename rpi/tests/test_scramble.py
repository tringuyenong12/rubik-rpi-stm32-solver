import unittest

from rubik_robot.cube.scramble import (
    apply_move,
    apply_moves,
    create_scramble_problem,
    explain_move,
    generate_scramble,
    parse_move_token,
)
from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string
from rubik_robot.solver.kociemba_solver import solve_cube


class TestScramble(unittest.TestCase):
    def test_parse_move_token(self):
        self.assertEqual(parse_move_token("R"), ("R", 1))
        self.assertEqual(parse_move_token("R'"), ("R", -1))
        self.assertEqual(parse_move_token("R3"), ("R", -1))
        self.assertEqual(parse_move_token("R2"), ("R", 2))
        self.assertEqual(parse_move_token("U1"), ("U", 1))

        with self.assertRaises(ValueError):
            parse_move_token("X")
        with self.assertRaises(ValueError):
            parse_move_token("")

    def test_apply_move_single(self):
        cube = apply_move(SOLVED_CUBE, "R")
        self.assertNotEqual(cube, SOLVED_CUBE)
        validate_cube_string(cube)

        # 4 identical 90-degree moves restore the face
        c4 = apply_moves(SOLVED_CUBE, ["R", "R", "R", "R"])
        self.assertEqual(c4, SOLVED_CUBE)

        # R followed by R' restores cube
        c_inv = apply_moves(SOLVED_CUBE, ["R", "R'"])
        self.assertEqual(c_inv, SOLVED_CUBE)

    def test_generate_scramble(self):
        easy = generate_scramble("easy")
        self.assertTrue(6 <= len(easy) <= 8)

        med = generate_scramble("medium")
        self.assertTrue(12 <= len(med) <= 15)

        hard = generate_scramble("hard")
        self.assertTrue(20 <= len(hard) <= 22)

        # Verify no consecutive identical faces
        for i in range(len(med) - 1):
            self.assertNotEqual(med[i][0], med[i + 1][0])

    def test_create_scramble_problem(self):
        problem = create_scramble_problem("easy")
        self.assertIn("scramble", problem)
        self.assertIn("cube", problem)
        self.assertIn("solution", problem)
        validate_cube_string(problem["cube"])

        # Solution applied to scrambled cube must restore SOLVED_CUBE
        if problem["solution"]:
            restored = apply_moves(problem["cube"], problem["solution"].split())
            self.assertEqual(restored, SOLVED_CUBE)

    def test_explain_move(self):
        vi_r = explain_move("R", "vi")
        self.assertIn("Phải", vi_r)

        en_u = explain_move("U'", "en")
        self.assertIn("Up", en_u)
        self.assertIn("counter-clockwise", en_u)


if __name__ == "__main__":
    unittest.main()
