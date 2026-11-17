"""Preview or send a validated solver solution using the STM32 UART protocol."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'rpi'))

from rubik_robot.solver.execution import solution_plan
from rubik_robot.transport.scramble_sender import send_actions, ScrambleSendError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--cube', help='54 stickers in URFDLB order, matching machine placement')
    source.add_argument('--input', type=Path, help='JSON containing cube and optionally solution')
    parser.add_argument('--solution', help="Optional known formula, e.g. R U_ F2")
    parser.add_argument('--output', type=Path, help='Export command bodies without transaction IDs')
    parser.add_argument('--port', help='Send only when a UART port is supplied')
    parser.add_argument('--baudrate', type=int, default=115200)
    parser.add_argument('--timeout', type=float, default=30, help='DONE timeout per physical command')
    args = parser.parse_args()
    try:
        data = json.loads(args.input.read_text(encoding='utf-8')) if args.input else {'cube': args.cube}
        formula = args.solution if args.solution is not None else data.get('solution')
        solution, actions = solution_plan(data['cube'], formula)
        bodies = ''.join(action.to_wire() + '\n' for action in actions)
        print('Solution:', solution or '<already solved>')
        print('Command bodies (UART adds #ID):\n' + bodies, end='')
        if args.output:
            args.output.write_text(bodies, encoding='utf-8')
        if args.port:
            result = send_actions(actions, args.port, args.baudrate, timeout_s=args.timeout,
                                  progress=lambda count, reply: print(f'{count}/{len(actions)} {reply}'))
            print('Completed logical moves:', result.completed)
        return 0
    except ScrambleSendError as error:
        print(f'UART stopped: {error.completed} complete moves; '
              f'{error.completed_quarter_turns} confirmed quarter turns in the failed move. {error}',
              file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('Interrupted; the current move may still be executing.', file=sys.stderr)
        return 130


if __name__ == '__main__':
    raise SystemExit(main())
