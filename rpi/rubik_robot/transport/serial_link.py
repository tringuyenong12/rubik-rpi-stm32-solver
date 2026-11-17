"""Compatibility facade: execute logical moves through Rubik_Cube helpers."""
from dataclasses import dataclass

from Rubik_Cube.motion import motion
from Rubik_Cube.UART_Command.UART_Command import UARTSession
from rubik_robot.protocol import Command, MoveCommand


class MoveExecutionError(RuntimeError):
    """Preserve completed quarter turns when a logical move fails part way."""
    def __init__(self, message, completed_quarter_turns):
        super().__init__(message)
        self.completed_quarter_turns = completed_quarter_turns


@dataclass
class SerialLink:
    port: str
    baudrate: int = 115200
    timeout_s: float = 30.0

    def __post_init__(self):
        self.session = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    @staticmethod
    def require_scan_support():
        raise NotImplementedError(
            "STM32 firmware has no SCAN_POSE command. Scan manually, then use "
            "scripts/run_solver.py with the scanned cube or saved solution JSON.")

    def open(self):
        if self.session is None:
            self.session = UARTSession(self.port, self.baudrate, self.timeout_s)
        self.session.open()

    def close(self):
        if self.session is not None:
            self.session.close()
            self.session = None

    def request(self, command: Command) -> str:
        return self.request_completed(command)

    def request_completed(self, command: Command, timeout_s=None) -> str:
        if self.session is None:
            raise RuntimeError("SerialLink is not open")
        if not isinstance(command, MoveCommand) and (command.name not in {'PING', 'RESET'} or command.args):
            raise ValueError(f"Unsupported STM32 command: {command.name}")
        if not isinstance(command, MoveCommand):
            return self.session.request(command.bodies()[0], timeout_s)
        completed = 0
        with self.session.lock:
            old_timeout = self.session.done_timeout
            if timeout_s is not None:
                self.session.done_timeout = timeout_s
            try:
                for token in command.tokens:
                    # Calls move_Front/move_Right/... via their short aliases.
                    if not getattr(motion, 'move_' + token)(session=self.session):
                        error = self.session.last_error or RuntimeError('Move failed')
                        raise MoveExecutionError(str(error), completed) from error
                    completed += 1
                return f'>#{self.session.command_id} DONE'
            finally:
                self.session.done_timeout = old_timeout
