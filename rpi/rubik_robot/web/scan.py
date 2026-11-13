"""Fixed whole-cube scan route, image orientation and acknowledged command queue."""

from __future__ import annotations

import numpy as np

from rubik_robot.cube.state import FACE_ORDER

# Right-handed frame: +X=R, +Y=U, +Z=F. Positive x/z follow R/F turns.
ROTATIONS = {
    "X": np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=int),
    "Z": np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]], dtype=int),
}
NORMALS = {"U": (0, 1, 0), "R": (1, 0, 0), "F": (0, 0, 1),
           "D": (0, -1, 0), "L": (-1, 0, 0), "B": (0, 0, -1)}
RIGHT = {"U": (1, 0, 0), "R": (0, 0, -1), "F": (1, 0, 0),
         "D": (1, 0, 0), "L": (0, 0, 1), "B": (-1, 0, 0)}
DOWN = {"U": (0, 0, 1), "R": (0, -1, 0), "F": (0, -1, 0),
        "D": (0, 0, -1), "L": (0, -1, 0), "B": (0, -1, 0)}


def fixed_route() -> list[dict]:
    """Input: none. Output: U,F,D,B,R,L captures and exact return-to-home rotations."""
    route = [{"kind": "capture", "face": "U"}]
    for face in "FDB":
        route += [{"kind": "reorient", "axis": "X", "turns": 1},
                  {"kind": "capture", "face": face}]
    route += [{"kind": "reorient", "axis": "X", "turns": 1},
              {"kind": "reorient", "axis": "Z", "turns": -1},
              {"kind": "capture", "face": "R"},
              {"kind": "reorient", "axis": "Z", "turns": 2},
              {"kind": "capture", "face": "L"},
              {"kind": "reorient", "axis": "Z", "turns": -1}]
    orientation = np.eye(3, dtype=int)
    for index, step in enumerate(route):
        step["id"] = index + 1
        if step["kind"] == "reorient":
            orientation = np.linalg.matrix_power(ROTATIONS[step["axis"]], step["turns"] % 4) @ orientation
            step["uart"] = f"REORIENT {step['axis']} {step['turns']} {800 * abs(step['turns'])}"
        else:
            step["orientation"] = orientation.tolist()
            if not np.array_equal(orientation @ NORMALS[step["face"]], [0, 1, 0]):
                raise ValueError("Kế hoạch quét có mặt không hướng lên camera.")
    if not np.array_equal(orientation, np.eye(3, dtype=int)):
        raise ValueError("Kế hoạch không trả khối về tư thế ban đầu.")
    return route


def canonical_face(raw: list, face: str, orientation: list) -> list:
    """Input: camera grid (top=B, right=R) and pose. Output: canonical face rows."""
    matrix = np.asarray(orientation, dtype=int)
    result = [None] * 9
    for row in range(3):
        for col in range(3):
            point = matrix @ (np.asarray(NORMALS[face]) + (col - 1) * np.asarray(RIGHT[face])
                              + (row - 1) * np.asarray(DOWN[face]))
            camera_row, camera_col = int(point[2] + 1), int(point[0] + 1)
            result[row * 3 + col] = raw[camera_row * 3 + camera_col]
    return result


def camera_face(canonical: list, face: str, orientation: list) -> list:
    """Input: canonical face and pose. Output: top-camera grid; inverse of canonical_face."""
    indices = canonical_face(list(range(9)), face, orientation)
    raw = [None] * 9
    for i, j in enumerate(indices):
        raw[j] = canonical[i]
    return raw


def assemble_faces(faces: dict[str, list[str]]) -> str:
    """Input: six canonical color grids. Output: URFDLB state mapped by center colors."""
    if set(faces) != set(FACE_ORDER) or any(len(f) != 9 for f in faces.values()):
        raise ValueError("Cần đủ sáu mặt, mỗi mặt chín sticker.")
    centers = {faces[f][4]: f for f in FACE_ORDER}
    if len(centers) != 6:
        raise ValueError("Sáu tâm trùng màu; kiểm tra calibration hoặc mặt đang quét.")
    try:
        return "".join(centers[color] for f in FACE_ORDER for color in faces[f])
    except KeyError as exc:
        raise ValueError("Sticker có màu không khớp sáu tâm.") from exc
