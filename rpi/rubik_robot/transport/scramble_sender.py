"""Send a scramble sequentially, counting only acknowledged completed moves."""

from dataclasses import dataclass
from threading import Event
from typing import Callable

from rubik_robot.protocol import Command
from rubik_robot.scramble import ScramblePlan
from rubik_robot.transport.serial_link import SerialLink


@dataclass(frozen=True)
class SendResult:
    """Number of completed turns and whether the remaining sequence was cancelled."""

    completed: int
    cancelled: bool


class ScrambleSendError(RuntimeError):
    """UART failure carrying the number of positively completed turns."""

    def __init__(self, message: str, completed: int, uncertain_move: bool):
        """Input: failure/progress. Output: an exception preserving partial-send status."""
        super().__init__(message)
        self.completed = completed
        self.uncertain_move = uncertain_move


def send_scramble(plan: ScramblePlan, port: str, baudrate: int = 115200,
                  cancel: Event | None = None, progress: Callable[[int, str], None] | None = None,
                  timeout_s: float = 10) -> SendResult:
    """Input: plan, port and cancellation/progress hooks. Output: completed/cancelled status."""
    if not port.strip() or baudrate <= 0 or timeout_s <= 0:
        raise ValueError('Specify a serial port, positive baud rate and timeout')
    completed = 0
    sending_move = False
    if cancel is not None and cancel.is_set():
        return SendResult(0, True)
    try:
        with SerialLink(port=port, baudrate=baudrate, timeout_s=timeout_s) as link:
            link.request_completed(Command('PING'))
            for action in plan.actions:
                if cancel is not None and cancel.is_set():
                    return SendResult(completed, True)
                sending_move = True
                response = link.request_completed(action.command)
                completed += 1
                sending_move = False
                if progress is not None:
                    progress(completed, response)
        return SendResult(completed, False)
    except Exception as error:
        raise ScrambleSendError(str(error), completed, sending_move) from error
