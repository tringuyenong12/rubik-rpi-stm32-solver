from __future__ import annotations

import argparse
from pathlib import Path

from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.protocol import Command
from rubik_robot.solver.kociemba_solver import solve_cube
from rubik_robot.transport.serial_link import SerialLink


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rubik solver robot controller")
    parser.add_argument(
        "--mode",
        choices=["demo", "solve", "send"],
        default="demo",
        help="demo: print pipeline, solve: solve cube string, send: send commands over UART",
    )
    parser.add_argument("--cube", default=SOLVED_CUBE, help="54-character cube string in URFDLB order")
    parser.add_argument("--port", default="/dev/ttyAMA0", help="UART serial port")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--duration-ms", type=int, default=450)
    parser.add_argument(
        "--face-turn-command",
        choices=["MOVE", "TURN"],
        default="TURN",
        help="TURN matches the mechanical actuator protocol; MOVE is kept for legacy debug",
    )
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    return parser


def run_demo(cube: str, duration_ms: int, face_turn_command: str) -> None:
    validate_cube_string(cube)
    solution = solve_cube(cube)
    planner = MotionPlanner(default_duration_ms=duration_ms, face_turn_command=face_turn_command)
    actions = planner.plan(solution)

    print("Cube:", cube)
    print("Solution:", solution or "<already solved>")
    print("Robot actions:")
    for action in actions:
        print(" ", action.to_wire())


def run_send(cube: str, port: str, baudrate: int, duration_ms: int, face_turn_command: str) -> None:
    validate_cube_string(cube)
    solution = solve_cube(cube)
    planner = MotionPlanner(default_duration_ms=duration_ms, face_turn_command=face_turn_command)
    actions = planner.plan(solution)

    with SerialLink(port=port, baudrate=baudrate, timeout_s=2.0) as link:
        print(link.request(Command("PING")))
        print(link.request(Command("HOME")))
        for action in actions:
            print("->", action.to_wire())
            print("<-", link.request(action.command))


def main() -> None:
    args = build_parser().parse_args()
    if args.mode in {"demo", "solve"}:
        run_demo(args.cube, args.duration_ms, args.face_turn_command)
    elif args.mode == "send":
        run_send(args.cube, args.port, args.baudrate, args.duration_ms, args.face_turn_command)


if __name__ == "__main__":
    main()

