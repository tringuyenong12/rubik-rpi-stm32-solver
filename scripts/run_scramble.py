"""Generate/export a solved-cube scramble and optionally send it over UART."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'rpi'))

from rubik_robot.scramble import LEVELS, create_scramble
from rubik_robot.transport.scramble_sender import ScrambleSendError, send_scramble


def main():
    """Input: difficulty/output/serial CLI options. Output: scramble frames and optional send result."""
    parser = argparse.ArgumentParser(description='Scramble a solved Rubik cube')
    parser.add_argument('--level', choices=tuple(LEVELS), default='easy')
    parser.add_argument('--seed', type=int, help='Repeat a generated problem')
    parser.add_argument('--output', type=Path, help='Save newline-delimited UART frames')
    parser.add_argument('--duration-ms', type=int, default=450)
    parser.add_argument('--face-turn-command', choices=('TURN', 'MOVE'), default='TURN')
    parser.add_argument('--port', help='Send to this serial port after generating')
    parser.add_argument('--baudrate', type=int, default=115200)
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args()
    try:
        plan = create_scramble(args.level, args.seed, args.duration_ms, args.face_turn_command)
        print(f'Start from solved | {plan.level} | {len(plan.moves)} moves')
        print(' '.join(plan.moves))
        print(plan.uart_text(), end='')
        print('Target cube', plan.cube)
        if args.output:
            args.output.write_text(plan.uart_text(), encoding='utf-8', newline='\n')
            print('Saved', args.output)
        if args.port:
            result = send_scramble(plan, args.port, args.baudrate, timeout_s=args.timeout,
                                   progress=lambda count, response: print(f'{count}/{len(plan.moves)} {response}'))
            print('Completed', result.completed)
    except ScrambleSendError as error:
        print(f'UART failed after {error.completed} completed moves: {error}', file=sys.stderr)
        if error.uncertain_move:
            print('The last transmitted turn is unconfirmed. Check cube state before another send.', file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted. A transmitted turn may still be executing.', file=sys.stderr)
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
