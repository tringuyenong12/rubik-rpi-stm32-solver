from __future__ import annotations

import random
from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string

FACES = ("U", "R", "F", "D", "L", "B")
MODIFIERS = ("", "'", "2")
OPPOSITE_FACES = {
    "U": "D", "D": "U",
    "L": "R", "R": "L",
    "F": "B", "B": "F",
}


def generate_scramble_sequence(length: int = 20) -> list[str]:
    """
    Tạo chuỗi nước đi trộn Rubik ngẫu nhiên chuẩn WCA.
    Đảm bảo:
    - Không có 2 bước liên tiếp trên cùng một mặt (vd: không có R R').
    - Không có 3 bước xung đột mặt đối diện (vd: không có R L R).
    """
    if length <= 0:
        return []

    moves: list[str] = []
    last_face = ""
    second_last_face = ""

    for _ in range(length):
        valid_faces = [f for f in FACES if f != last_face]
        if last_face and second_last_face == OPPOSITE_FACES.get(last_face):
            valid_faces = [f for f in valid_faces if f != second_last_face]

        face = random.choice(valid_faces)
        modifier = random.choice(MODIFIERS)
        moves.append(f"{face}{modifier}")

        second_last_face = last_face
        last_face = face

    return moves


def _rotate_face_cw(face_chars: list[str]) -> list[str]:
    """Xoay 9 ô của 1 mặt theo chiều kim đồng hồ."""
    return [
        face_chars[6], face_chars[3], face_chars[0],
        face_chars[7], face_chars[4], face_chars[1],
        face_chars[8], face_chars[5], face_chars[2]
    ]


def apply_move(cube_str: str, move: str) -> str:
    """
    Mô phỏng tác động của 1 bước xoay lên chuỗi trạng thái 54 ký tự (URFDLB).
    """
    validate_cube_string(cube_str)
    if not move:
        return cube_str

    face = move[0]
    if face not in "URFDLB":
        raise ValueError(f"Mặt không hợp lệ: {face}")

    turns = 1
    if len(move) > 1:
        if move[1] == "'":
            turns = 3
        elif move[1] == "2":
            turns = 2
        else:
            raise ValueError(f"Hậu tố nước đi không hợp lệ: {move}")

    c = list(cube_str)
    idx_map = {"U": 0, "R": 9, "F": 18, "D": 27, "L": 36, "B": 45}

    for _ in range(turns):
        # 1. Xoay 9 ô của chính mặt đó
        f_idx = idx_map[face]
        c[f_idx:f_idx + 9] = _rotate_face_cw(c[f_idx:f_idx + 9])

        # 2. Hoán vị 4 dải 3 ô của các mặt lân cận
        if face == "U":
            b = [c[45], c[46], c[47]]
            r = [c[9], c[10], c[11]]
            f = [c[18], c[19], c[20]]
            l = [c[36], c[37], c[38]]
            c[9], c[10], c[11] = b
            c[18], c[19], c[20] = r
            c[36], c[37], c[38] = f
            c[45], c[46], c[47] = l
        elif face == "D":
            f = [c[24], c[25], c[26]]
            r = [c[15], c[16], c[17]]
            b = [c[51], c[52], c[53]]
            l = [c[42], c[43], c[44]]
            c[15], c[16], c[17] = f
            c[51], c[52], c[53] = r
            c[42], c[43], c[44] = b
            c[24], c[25], c[26] = l
        elif face == "F":
            u = [c[6], c[7], c[8]]
            r = [c[9], c[12], c[15]]
            d = [c[29], c[28], c[27]]
            l = [c[44], c[41], c[38]]
            c[9], c[12], c[15] = u
            c[29], c[28], c[27] = r
            c[44], c[41], c[38] = d
            c[6], c[7], c[8] = l
        elif face == "B":
            u = [c[2], c[1], c[0]]
            l = [c[36], c[39], c[42]]
            d = [c[33], c[34], c[35]]
            r = [c[17], c[14], c[11]]
            c[36], c[39], c[42] = u
            c[33], c[34], c[35] = l
            c[17], c[14], c[11] = d
            c[2], c[1], c[0] = r
        elif face == "L":
            u = [c[0], c[3], c[6]]
            f = [c[18], c[21], c[24]]
            d = [c[27], c[30], c[33]]
            b = [c[53], c[50], c[47]]
            c[18], c[21], c[24] = u
            c[27], c[30], c[33] = f
            c[53], c[50], c[47] = d
            c[0], c[3], c[6] = b
        elif face == "R":
            u = [c[8], c[5], c[2]]
            b = [c[45], c[48], c[51]]
            d = [c[35], c[32], c[29]]
            f = [c[26], c[23], c[20]]
            c[45], c[48], c[51] = u
            c[35], c[32], c[29] = b
            c[26], c[23], c[20] = d
            c[8], c[5], c[2] = f

    return "".join(c)


def apply_moves(cube_str: str, moves: list[str] | str) -> str:
    """
    Áp dụng một chuỗi các nước đi lên khối Rubik.
    moves có thể là danh sách ['R', 'U', "R'"] hoặc chuỗi "R U R'".
    """
    if isinstance(moves, str):
        moves = moves.strip().split()

    current_cube = cube_str
    for m in moves:
        current_cube = apply_move(current_cube, m)
    return current_cube


def scramble_cube(length: int = 20, start_cube: str = SOLVED_CUBE) -> tuple[list[str], str]:
    """
    Hàm tổng hợp: Trộn khối Rubik ngẫu nhiên.
    Trả về: (danh_sách_nước_trộn, chuỗi_54_ký_tự_kết_quả)
    """
    scramble_moves = generate_scramble_sequence(length=length)
    scrambled_cube_str = apply_moves(start_cube, scramble_moves)
    return scramble_moves, scrambled_cube_str
