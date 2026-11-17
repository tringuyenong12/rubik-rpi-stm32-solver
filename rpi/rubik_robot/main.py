from __future__ import annotations

import argparse
from pathlib import Path

from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string
from rubik_robot.protocol import Command
from rubik_robot.solver.execution import solution_plan
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
    parser.add_argument("--port", default="/dev/serial0", help="UART serial port")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--duration-ms", type=int, default=450)
    parser.add_argument(
        "--face-turn-command",
        choices=["MOVE", "TURN"],
        default="MOVE",
        help="Deprecated compatibility option; always sends RUBIK MOVE",
    )
    parser.add_argument("--log-dir", type=Path, default=Path("logs"))
    return parser


def run_demo(cube: str, duration_ms: int, face_turn_command: str) -> None:
    validate_cube_string(cube)
    solution, actions = solution_plan(cube, duration_ms=duration_ms)

    print("Cube:", cube)
    print("Solution:", solution or "<already solved>")
    print("Robot actions:")
    for action in actions:
        print(" ", action.to_wire())


def run_send(cube: str, port: str, baudrate: int, duration_ms: int, face_turn_command: str) -> None:
    validate_cube_string(cube)
    solution, actions = solution_plan(cube, duration_ms=duration_ms)

    if not actions:
        print('Cube is already solved; no UART commands needed.')
        return

    with SerialLink(port=port, baudrate=baudrate, timeout_s=30.0) as link:
        print(link.request(Command("PING")))
        print(link.request(Command("RESET")))
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

