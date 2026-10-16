from __future__ import annotations

import argparse
from pathlib import Path
import sys

# Đảm bảo có thể chạy trực tiếp python main.py mà không bị lỗi ModuleNotFoundError: No module named 'rubik_robot'
PACKAGE_ROOT = Path(__file__).resolve().parent.parent
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# Windows terminals configured with a legacy code page otherwise fail before
# the controller can print its result.  Raspberry Pi terminals are already
# UTF-8, so this is a no-op there.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rubik_robot.cube.scramble import generate_scramble_sequence, scramble_cube
from rubik_robot.cube.state import SOLVED_CUBE, validate_cube_string
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.protocol import Command
from rubik_robot.solver.kociemba_solver import solve_cube
from rubik_robot.transport.serial_link import SerialLink, Stm32BinaryLink


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rubik solver robot controller")
    parser.add_argument(
        "--mode",
        choices=["demo", "solve", "send", "scramble"],
        default="demo",
        help="demo: print pipeline, solve: solve cube string, send: send commands over UART, scramble: random scramble",
    )
    parser.add_argument("--cube", default=SOLVED_CUBE, help="54-character cube string in URFDLB order")
    parser.add_argument("--scramble-length", "--length", type=int, default=20, help="Number of moves for random scramble")
    parser.add_argument("--port", default="/dev/serial0", help="UART serial port (RPi stable alias: /dev/serial0)")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--duration-ms", type=int, default=450)
    parser.add_argument(
        "--face-turn-command",
        choices=["MOVE", "TURN"],
        default="TURN",
        help="TURN matches the mechanical actuator protocol; MOVE is kept for legacy debug",
    )
    parser.add_argument(
        "--uart-protocol",
        choices=["binary", "text"],
        default="binary",
        help="binary: framed CRC/ACK protocol for the 8-servo STM32 firmware; text: legacy ASCII protocol",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="For --mode scramble, send every generated move to STM32 after printing the 54-character state",
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


def run_scramble(
    length: int,
    duration_ms: int,
    face_turn_command: str,
    *,
    execute: bool = False,
    port: str = "/dev/serial0",
    baudrate: int = 115200,
    uart_protocol: str = "binary",
) -> None:
    moves, scrambled_cube = scramble_cube(length=length)
    print(f"=== TRỘN RUBIK NGẪU NHIÊN ({length} BƯỚC) ===")
    print("Nước đi trộn:", " ".join(moves))
    print("Chuỗi 54 ký tự sau khi trộn:")
    print(scrambled_cube)
    print("\nLập kế hoạch để robot tự trộn trên bàn máy (Scramble actions):")
    planner = MotionPlanner(default_duration_ms=duration_ms, face_turn_command=face_turn_command)
    scramble_actions = planner.plan(" ".join(moves))
    for action in scramble_actions:
        print(" ", action.to_wire())

    if execute:
        print("\nGửi từng lệnh trộn qua UART (ACK/DONE cho mỗi bước):")
        _send_actions(scramble_actions, port, baudrate, uart_protocol)

    print("\nKiểm tra giải lại bằng Kociemba:")
    solution = solve_cube(scrambled_cube)
    print("Lời giải:", solution)


def _send_actions(actions, port: str, baudrate: int, uart_protocol: str) -> None:
    if uart_protocol == "binary":
        with Stm32BinaryLink(port=port, baudrate=baudrate) as link:
            print("<-", link.ping())
            print("<-", link.home())
            for index, action in enumerate(actions, start=1):
                print(f"-> [{index}] {action.to_wire()}")
                print("<-", link.request_move(action.command))
            print("<-", link.finish())
        return

    # Kept only for the repository's existing line-based prototype firmware.
    with SerialLink(port=port, baudrate=baudrate, timeout_s=2.0) as link:
        print(link.request(Command("PING")))
        print(link.request(Command("HOME")))
        for action in actions:
            print("->", action.to_wire())
            print("<-", link.request(action.command))


def run_send(
    cube: str,
    port: str,
    baudrate: int,
    duration_ms: int,
    face_turn_command: str,
    uart_protocol: str,
) -> None:
    validate_cube_string(cube)
    solution = solve_cube(cube)
    planner = MotionPlanner(default_duration_ms=duration_ms, face_turn_command=face_turn_command)
    actions = planner.plan(solution)

    _send_actions(actions, port, baudrate, uart_protocol)


def main() -> None:
    args = build_parser().parse_args()
    if args.mode in {"demo", "solve"}:
        run_demo(args.cube, args.duration_ms, args.face_turn_command)
    elif args.mode == "scramble":
        run_scramble(
            args.scramble_length,
            args.duration_ms,
            args.face_turn_command,
            execute=args.execute,
            port=args.port,
            baudrate=args.baudrate,
            uart_protocol=args.uart_protocol,
        )
    elif args.mode == "send":
        run_send(
            args.cube,
            args.port,
            args.baudrate,
            args.duration_ms,
            args.face_turn_command,
            args.uart_protocol,
        )


if __name__ == "__main__":
    main()
