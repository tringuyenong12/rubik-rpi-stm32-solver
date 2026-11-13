import pytest

from rubik_robot.cube.state import CubeStateError, SOLVED_CUBE, validate_cube_string


def test_validate_solved_cube():
    validate_cube_string(SOLVED_CUBE)


def test_rejects_wrong_length():
    with pytest.raises(CubeStateError):
        validate_cube_string("U")

