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

