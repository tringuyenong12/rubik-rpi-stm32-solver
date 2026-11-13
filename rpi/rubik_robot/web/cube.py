"""Validated cube operations shared by the three web modes."""

from __future__ import annotations

import random
import re

from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE, validate_cube_string
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.solver.kociemba_solver import solve_cube
from twophase.cubie import CUBE_OK, CubieCube, moveCube
from twophase.enums import Move
from twophase.face import FaceCube

LEVELS = {"easy": 5, "medium": 12, "hard": 22}
MOVE_PATTERN = re.compile(r"^[URFDLB](?:2|')?$")


def validated_cube(state: str) -> CubieCube:
    """Input: URFDLB state. Output: valid CubieCube; raise ValueError if impossible."""
    validate_cube_string(state)
    if any(state[i * 9 + 4] != face for i, face in enumerate(FACE_ORDER)):
        raise ValueError("Sáu tâm phải đúng thứ tự URFDLB; kiểm tra hướng và màu tâm.")
    face_cube = FaceCube()
    result = face_cube.from_string(state)
    if result != CUBE_OK:
        raise ValueError(str(result))
    cube = face_cube.to_cubie_cube()
    if sorted(cube.cp) != list(range(8)) or sorted(cube.ep) != list(range(12)):
        raise ValueError("Có viên góc/cạnh thiếu hoặc trùng; kiểm tra lại màu và hướng các mặt.")
    result = cube.verify()
    if result != CUBE_OK:
        raise ValueError(str(result))
    return cube


def apply_moves(state: str, moves: str | list[str]) -> str:
    """Input: valid state and standard moves. Output: resulting URFDLB state."""
    cube = validated_cube(state)
    for token in moves.split() if isinstance(moves, str) else moves:
        if not MOVE_PATTERN.fullmatch(token):
            raise ValueError(f"Nước xoay không hợp lệ: {token}")
        suffix = {"": "1", "2": "2", "'": "3"}[token[1:]]
        cube.multiply(moveCube[Move[token[0] + suffix]])
    return cube.to_facelet_cube().to_string()


def inverse_moves(moves: list[str]) -> list[str]:
    """Input: standard move list. Output: reversed inverse sequence."""
    return [m if m.endswith("2") else m[:-1] if m.endswith("'") else m + "'"
            for m in reversed(moves)]


def uart_lines(moves: list[str], duration_ms: int = 450) -> list[str]:
    """Input: face moves and quarter-turn time. Output: TURN lines, without I/O."""
    if not 50 <= duration_ms <= 10000:
        raise ValueError("Thời gian một phần tư vòng phải từ 50 đến 10000 ms.")
    return [a.to_wire() for a in MotionPlanner(duration_ms, "TURN").plan(" ".join(moves))]


def solution_for(state: str) -> dict:
    """Input: cube state. Output: verified solution, states and UART payload."""
    validated_cube(state)
    moves = solve_cube(state).split()
    if apply_moves(state, moves) != SOLVED_CUBE:
        raise ValueError("Không xác minh được lời giải; không xuất lệnh UART.")
    states = [state]
    for move in moves:
        states.append(apply_moves(states[-1], [move]))
    return {"state": state, "moves": moves, "states": states,
            "uart": uart_lines(moves), "count": len(moves)}


def scramble_for(level: str, seed: int | None = None) -> dict:
    """Input: level and optional seed. Output: scramble, resulting state and solution."""
    if level not in LEVELS:
        raise ValueError("Mức độ phải là easy, medium hoặc hard.")
    rng = random.Random(seed)
    moves: list[str] = []
    axes = {"U": 0, "D": 0, "R": 1, "L": 1, "F": 2, "B": 2}
    while len(moves) < LEVELS[level]:
        face = rng.choice(FACE_ORDER)
        if moves and axes[face] == axes[moves[-1][0]]:
            continue
        moves.append(face + rng.choice(["", "'", "2"]))
    state = apply_moves(SOLVED_CUBE, moves)
    solution = solution_for(state)
    return {"level": level, "seed": seed, "scramble": moves, "state": state,
            "scramble_uart": uart_lines(moves), "solution": solution,
            "inverse": inverse_moves(moves),
            "difficulty_basis": "Độ dài chuỗi trộn 5/12/22 nước; không phải độ sâu tối ưu."}


