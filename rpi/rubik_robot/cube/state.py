from __future__ import annotations

from collections import Counter


FACE_ORDER = "URFDLB"
SOLVED_CUBE = "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"


class CubeStateError(ValueError):
    """Raised when a cube string is malformed before reaching the solver."""


def validate_cube_string(cube: str) -> None:
    if len(cube) != 54:
        raise CubeStateError(f"Cube string must contain 54 stickers, got {len(cube)}")

    invalid = sorted(set(cube) - set(FACE_ORDER))
    if invalid:
        raise CubeStateError(f"Invalid sticker symbols: {invalid}. Expected only {FACE_ORDER}")

    counts = Counter(cube)
    wrong_counts = {face: counts[face] for face in FACE_ORDER if counts[face] != 9}
    if wrong_counts:
        raise CubeStateError(f"Each face color must appear 9 times, got {wrong_counts}")


def facelets(cube: str) -> dict[str, str]:
    validate_cube_string(cube)
    return {
        "U": cube[0:9],
        "R": cube[9:18],
        "F": cube[18:27],
        "D": cube[27:36],
        "L": cube[36:45],
        "B": cube[45:54],
    }

