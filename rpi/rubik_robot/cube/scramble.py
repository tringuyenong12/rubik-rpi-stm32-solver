from __future__ import annotations

import random
from typing import Literal

from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE, validate_cube_string
from rubik_robot.solver.kociemba_solver import solve_cube
import twophase.cubie as cb
import twophase.enums as en
import twophase.face as fc

# Face enum lookup
_FACE_ENUM = {
    "U": en.Color.U,
    "R": en.Color.R,
    "F": en.Color.F,
    "D": en.Color.D,
    "L": en.Color.L,
    "B": en.Color.B,
}

# Opposites and axis groupings to avoid redundant moves like R L R or R R'
_OPPOSITE_FACES = {
    "U": "D",
    "D": "U",
    "R": "L",
    "L": "R",
    "F": "B",
    "B": "F",
}

_MOVE_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "U": {"vi": "Xoay mặt Trên (Up) 90° cùng chiều kim đồng hồ", "en": "Turn Up face 90° clockwise"},
    "U'": {"vi": "Xoay mặt Trên (Up) 90° ngược chiều kim đồng hồ", "en": "Turn Up face 90° counter-clockwise"},
    "U2": {"vi": "Xoay mặt Trên (Up) 180°", "en": "Turn Up face 180°"},
    "D": {"vi": "Xoay mặt Dưới (Down) 90° cùng chiều kim đồng hồ", "en": "Turn Down face 90° clockwise"},
    "D'": {"vi": "Xoay mặt Dưới (Down) 90° ngược chiều kim đồng hồ", "en": "Turn Down face 90° counter-clockwise"},
    "D2": {"vi": "Xoay mặt Dưới (Down) 180°", "en": "Turn Down face 180°"},
    "R": {"vi": "Xoay mặt Phải (Right) 90° cùng chiều kim đồng hồ", "en": "Turn Right face 90° clockwise"},
    "R'": {"vi": "Xoay mặt Phải (Right) 90° ngược chiều kim đồng hồ", "en": "Turn Right face 90° counter-clockwise"},
    "R2": {"vi": "Xoay mặt Phải (Right) 180°", "en": "Turn Right face 180°"},
    "L": {"vi": "Xoay mặt Trái (Left) 90° cùng chiều kim đồng hồ", "en": "Turn Left face 90° clockwise"},
    "L'": {"vi": "Xoay mặt Trái (Left) 90° ngược chiều kim đồng hồ", "en": "Turn Left face 90° counter-clockwise"},
    "L2": {"vi": "Xoay mặt Trái (Left) 180°", "en": "Turn Left face 180°"},
    "F": {"vi": "Xoay mặt Trước (Front) 90° cùng chiều kim đồng hồ", "en": "Turn Front face 90° clockwise"},
    "F'": {"vi": "Xoay mặt Trước (Front) 90° ngược chiều kim đồng hồ", "en": "Turn Front face 90° counter-clockwise"},
    "F2": {"vi": "Xoay mặt Trước (Front) 180°", "en": "Turn Front face 180°"},
    "B": {"vi": "Xoay mặt Sau (Back) 90° cùng chiều kim đồng hồ", "en": "Turn Back face 90° clockwise"},
    "B'": {"vi": "Xoay mặt Sau (Back) 90° ngược chiều kim đồng hồ", "en": "Turn Back face 90° counter-clockwise"},
    "B2": {"vi": "Xoay mặt Sau (Back) 180°", "en": "Turn Back face 180°"},
}


def explain_move(move: str, lang: str = "vi") -> str:
    """Return beginner-friendly description of a move in Vietnamese or English."""
    normalized = move.replace("3", "'").replace("1", "")
    info = _MOVE_DESCRIPTIONS.get(normalized)
    if info:
        return info.get(lang, info["en"])
    return f"Move {move}"


def parse_move_token(token: str) -> tuple[str, int]:
    """Parse a move token into face and turn count (1, -1, or 2)."""
    token = token.strip()
    if not token:
        raise ValueError("Empty move token")
    face = token[0].upper()
    if face not in FACE_ORDER:
        raise ValueError(f"Invalid face in move token: {token}")

    suffix = token[1:]
    if suffix in {"", "1"}:
        return face, 1
    if suffix in {"'", "3"}:
        return face, -1
    if suffix == "2":
        return face, 2
    raise ValueError(f"Invalid move suffix: {token}")


def apply_move(cube: str, move: str) -> str:
    """Apply a single move to a 54-character cube string."""
    validate_cube_string(cube)
    face, turns = parse_move_token(move)

    fcube = fc.FaceCube()
    fcube.from_string(cube)
    ccube = fcube.to_cubie_cube()

    # In twophase, multiplying by basicMoveCube[face] performs a 90° CW turn.
    # turns == 1: 1 turn; turns == 2: 2 turns; turns == -1 (or 3): 3 turns.
    count = 1 if turns == 1 else (2 if turns == 2 else 3)
    move_cube = cb.basicMoveCube[_FACE_ENUM[face]]
    for _ in range(count):
        ccube.multiply(move_cube)

    return ccube.to_facelet_cube().to_string()


def apply_moves(cube: str, moves: list[str] | str) -> str:
    """Apply a sequence of moves to a cube string."""
    if isinstance(moves, str):
        tokens = moves.split()
    else:
        tokens = moves

    curr = cube
    for token in tokens:
        curr = apply_move(curr, token)
    return curr


def generate_scramble(level: str = "medium", length: int | None = None) -> list[str]:
    """Generate a valid scramble move sequence according to difficulty level.
    
    Levels:
      - 'easy': 6-8 moves
      - 'medium': 12-15 moves
      - 'hard': 20-22 moves
    """
    if length is None:
        if level == "easy":
            length = random.randint(6, 8)
        elif level == "hard":
            length = random.randint(20, 22)
        else:  # medium
            length = random.randint(12, 15)

    suffixes = ["", "'", "2"]
    faces = list(FACE_ORDER)

    moves: list[str] = []
    last_face = ""
    second_last_face = ""

    while len(moves) < length:
        f = random.choice(faces)
        # Avoid same face consecutively (e.g. R R')
        if f == last_face:
            continue
        # Avoid redundant opposite face sequences like R L R
        if f == second_last_face and last_face == _OPPOSITE_FACES.get(f):
            continue

        suffix = random.choice(suffixes)
        moves.append(f"{f}{suffix}")
        second_last_face = last_face
        last_face = f

    return moves


def create_scramble_problem(level: str = "medium") -> dict:
    """Generate a complete scramble problem with scramble, cube state, and solution.
    
    Fulfills project requirement:
    'Mỗi đề bài cần lưu được scramble, trạng thái cube sau khi trộn và đáp án giải.'
    """
    scramble_moves = generate_scramble(level=level)
    scramble_str = " ".join(scramble_moves)
    scrambled_cube = apply_moves(SOLVED_CUBE, scramble_moves)
    solution_str = solve_cube(scrambled_cube)

    return {
        "level": level,
        "scramble": scramble_str,
        "scramble_moves": scramble_moves,
        "cube": scrambled_cube,
        "solution": solution_str,
        "solution_moves": solution_str.split() if solution_str else [],
        "move_count": len(solution_str.split()) if solution_str else 0,
    }
