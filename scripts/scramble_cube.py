"""
Script trộn Rubik ngẫu nhiên và mô phỏng trạng thái 54 ký tự
"""

from pathlib import Path
import sys

# Thêm thư mục rpi vào sys.path để import được rubik_robot
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RPI_DIR = PROJECT_ROOT / "rpi"
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from rubik_robot.cube.scramble import generate_scramble_sequence, scramble_cube
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.solver.kociemba_solver import solve_cube


def main() -> None:
    length = 20
    if len(sys.argv) > 1:
        try:
            length = int(sys.argv[1])
        except ValueError:
            pass

    moves, scrambled_cube = scramble_cube(length=length)

    print("=" * 65)
    print(f"       CHƯƠNG TRÌNH TRỘN RUBIK NGẪU NHIÊN ({length} BƯỚC)")
    print("=" * 65)
    print("\n1. Nước đi trộn ngẫu nhiên (Scramble moves):")
    print("  ", " ".join(moves))

    print("\n2. Chuỗi 54 ký tự sau khi trộn (Facelet string):")
    print("  ", scrambled_cube)

    print("\n3. Lệnh điều khiển gửi xuống robot để robot tự trộn trên bàn máy:")
    planner = MotionPlanner(default_duration_ms=450, face_turn_command="TURN")
    actions = planner.plan(" ".join(moves))
    for idx, act in enumerate(actions, 1):
        print(f"   {idx:2d}. {act.to_wire()}")

    print("\n4. Kiểm tra thuật toán Kociemba giải lại trạng thái này:")
    solution = solve_cube(scrambled_cube)
    print("   Lời giải:", solution or "<already solved>")
    print("=" * 65)


if __name__ == "__main__":
    main()
