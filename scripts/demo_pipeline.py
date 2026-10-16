from pathlib import Path
import sys

# Thêm thư mục rpi vào sys.path để import được rubik_robot
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RPI_DIR = PROJECT_ROOT / "rpi"
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.solver.kociemba_solver import solve_cube


def main() -> None:
    solution = solve_cube(SOLVED_CUBE)
    actions = MotionPlanner().plan(solution)
    print("solution:", solution or "<already solved>")
    print("actions:", [action.to_wire() for action in actions])


if __name__ == "__main__":
    main()
