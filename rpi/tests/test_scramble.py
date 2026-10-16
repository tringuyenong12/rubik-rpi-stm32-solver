from rubik_robot.cube.scramble import apply_move, apply_moves, generate_scramble_sequence, scramble_cube
from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string


def test_generate_scramble_length():
    moves = generate_scramble_sequence(20)
    assert len(moves) == 20
    # Đảm bảo không có 2 bước cùng mặt liên tiếp
    for i in range(len(moves) - 1):
        assert moves[i][0] != moves[i + 1][0]


def test_four_turns_identity():
    # Xoay 4 lần 90 độ cùng 1 mặt phải trả về nguyên vẹn trạng thái ban đầu
    cube = SOLVED_CUBE
    for _ in range(4):
        cube = apply_move(cube, "R")
    assert cube == SOLVED_CUBE

    for _ in range(4):
        cube = apply_move(cube, "U")
    assert cube == SOLVED_CUBE


def test_inverse_move():
    cube = apply_move(SOLVED_CUBE, "R")
    cube = apply_move(cube, "R'")
    assert cube == SOLVED_CUBE


def test_scramble_cube_valid_state():
    moves, scrambled = scramble_cube(length=20)
    assert len(moves) == 20
    validate_cube_string(scrambled)
