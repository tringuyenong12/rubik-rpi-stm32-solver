from __future__ import annotations

import re

from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string


def normalize_twophase_solution(raw_solution: str) -> str:
    """Normalize twophase output (e.g. 'D2 L3 U1 (20f)') to standard notation ('D2 L\' U')."""
    cleaned = re.sub(r"\s*\(\d+f\)\s*$", "", raw_solution.strip())
    if not cleaned:
        return ""

    tokens = cleaned.split()
    normalized: list[str] = []
    for token in tokens:
        if len(token) >= 2 and token[0] in "URFDLB":
            face = token[0]
            suffix = token[1:]
            if suffix == "1":
                normalized.append(face)
            elif suffix == "2":
                normalized.append(f"{face}2")
            elif suffix == "3":
                normalized.append(f"{face}'")
            else:
                normalized.append(token)
        else:
            normalized.append(token)
    return " ".join(normalized)


def solve_cube(cube: str, max_length: int = 20, timeout: int = 2) -> str:
    validate_cube_string(cube)
    if cube == SOLVED_CUBE:
        return ""

    # 1. First priority: Pure-python Herbert Kociemba 2-phase package
    try:
        import twophase.solver as sv  # type: ignore[import-not-found]

        raw = sv.solve(cube, max_length, timeout)
        # In twophase, error messages do not contain moves
        if raw.startswith("Error") or "invalid" in raw.lower() or "error" in raw.lower():
            raise RuntimeError(f"twophase solver returned error: {raw}")
        return normalize_twophase_solution(raw)
    except ImportError:
        pass

    # 2. Fallback: External kociemba C-wrapper package
    try:
        import kociemba  # type: ignore[import-not-found]

        return kociemba.solve(cube)
    except ImportError as exc:
        raise RuntimeError(
            "Neither 'twophase' package nor 'kociemba' is available. "
            "Ensure 'rpi/twophase' is present or run: pip install -r requirements.txt"
        ) from exc


