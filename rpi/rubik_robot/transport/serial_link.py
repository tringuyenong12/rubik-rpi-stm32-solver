from __future__ import annotations

import time
from dataclasses import dataclass

from rubik_robot.protocol import Command


@dataclass
class SerialLink:
    port: str
    baudrate: int = 115200
    timeout_s: float = 2.0

    def __post_init__(self) -> None:
        self._serial = None

    def __enter__(self) -> "SerialLink":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        import serial

        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout_s)
        time.sleep(0.2)

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def request(self, command: Command) -> str:
        if self._serial is None:
            raise RuntimeError("SerialLink is not open")

        frame = command.to_wire().encode("utf-8") + b"\n"
        self._serial.write(frame)
        self._serial.flush()
        response = self._serial.readline().decode("utf-8", errors="replace").strip()
        if not response:
            raise TimeoutError(f"No response for command: {command.to_wire()}")
        if response.startswith("ERR"):
            raise RuntimeError(response)
        return response

    def request_completed(self, command: Command, timeout_s: float | None = None) -> str:
        """Input: command/deadline. Output: matching DONE, or OK PONG for PING."""
        if self._serial is None:
            raise RuntimeError('SerialLink is not open')
        timeout_s = self.timeout_s if timeout_s is None else timeout_s
        if timeout_s <= 0:
            raise ValueError('Timeout must be positive')
        serial = self._serial
        old_timeout = serial.timeout
        serial.write(command.to_wire().encode('ascii') + b'\n')
        serial.flush()
        deadline = time.monotonic() + timeout_s
        buffer = bytearray()
        acknowledged = False
        try:
            while time.monotonic() < deadline:
                serial.timeout = min(.2, max(.001, deadline - time.monotonic()))
                buffer.extend(serial.readline())
                if len(buffer) > 4096:
                    raise RuntimeError('UART response exceeds 4096 bytes')
                while b'\n' in buffer:
                    line, _, remaining = buffer.partition(b'\n')
                    buffer = bytearray(remaining)
                    response = line.decode('ascii', errors='replace').strip()
                    if response.startswith('ERR'):
                        raise RuntimeError(response)
                    if command.name == 'PING' and response == 'OK PONG':
                        return response
                    if response == f'OK {command.name}':
                        acknowledged = True
                    if acknowledged and response == f'DONE {command.name}':
                        return response
            raise TimeoutError(f'Waiting for completion of {command.to_wire()}')
        finally:
            serial.timeout = old_timeout

