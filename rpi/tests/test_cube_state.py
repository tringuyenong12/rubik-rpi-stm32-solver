import unittest

from rubik_robot.cube.state import CubeStateError, SOLVED_CUBE, validate_cube_string


class TestCubeState(unittest.TestCase):
    def test_validate_solved_cube(self):
        validate_cube_string(SOLVED_CUBE)

    def test_rejects_wrong_length(self):
        with self.assertRaises(CubeStateError):
            validate_cube_string("U")


if __name__ == "__main__":
    unittest.main()

