from __future__ import annotations

from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string


def solve_cube(cube: str) -> str:
    validate_cube_string(cube)
    if cube == SOLVED_CUBE:
        return ""

    try:
        import kociemba
    except ImportError as exc:
        raise RuntimeError(
            "Package 'kociemba' is required for non-solved cube states. "
            "Install dependencies with: pip install -r requirements.txt"
        ) from exc

    return kociemba.solve(cube)

