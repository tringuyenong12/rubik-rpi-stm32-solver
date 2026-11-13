from __future__ import annotations

import time
import secrets
from dataclasses import dataclass

from rubik_robot.protocol import Command


@dataclass
class SerialLink:
    port: str
    baudrate: int = 115200
    timeout_s: float = 2.0
    handshake_attempts: int = 3
    motion_timeout_s: float = 65.0

    def __post_init__(self) -> None:
        self._serial = None
        self.connected = False
        self._used_tags: set[str] = set()
        if self.timeout_s <= 0 or self.motion_timeout_s <= 0 or self.handshake_attempts < 1:
            raise ValueError("Timeout and handshake attempts must be positive")

    def __enter__(self) -> "SerialLink":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        import serial

        if self.connected:
            return
        self.close()
        try:
            self._serial = serial.Serial(
                self.port, self.baudrate, timeout=self.timeout_s,
                write_timeout=self.timeout_s,
            )
            self._serial.reset_input_buffer()
            for _ in range(self.handshake_attempts):
                tag = self._new_tag()
                self._write(Command("PING").to_wire(tag))
                try:
                    self._wait_for(f"#{tag} ACK")
                except TimeoutError:
                    continue
                self.connected = True
                return
            raise TimeoutError("STM32 handshake timed out")
        except Exception as exc:
            self.close()
            raise ConnectionError(f"UART connection failed on {self.port}: {exc}") from exc

    def close(self) -> None:
        self.connected = False
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def request(self, command: Command, tag: str | None = None) -> str:
        if self._serial is None or not self.connected:
            raise RuntimeError("UART handshake required before sending commands")
        if tag is None:
            tag = self._new_tag()
        else:
            command.to_wire(tag)  # Validate before reserving the tag.
            if tag in self._used_tags:
                raise ValueError(f"Tag already used: {tag}")
            self._used_tags.add(tag)
        try:
            self._write(command.to_wire(tag))
            ack = f"#{tag} ACK"
            response = self._wait_for(ack)
            if command.expects_done:
                response = self._wait_for(
                    f"#{tag} DONE", timeout_s=max(self.timeout_s, self.motion_timeout_s)
                )
            return response
        except (OSError, TimeoutError, ConnectionError):
            self.close()
            raise

    def check_connection(self) -> bool:
        """Probe the link on demand; no background heartbeat thread."""
        if not self.connected:
            return False
        try:
            self.request(Command("PING"))
            return True
        except (OSError, RuntimeError):
            self.close()
            return False

    def _new_tag(self) -> str:
        tag = secrets.token_hex(8)
        while tag in self._used_tags:
            tag = secrets.token_hex(8)
        self._used_tags.add(tag)
        return tag

    def _write(self, line: str) -> None:
        frame = line.encode("ascii") + b"\n"
        if b"\n" in frame[:-1] or b"\r" in frame or len(frame) > 96:
            raise ValueError("Invalid UART frame")
        if self._serial.write(frame) != len(frame):
            raise ConnectionError("Incomplete UART write")

    def _wait_for(self, expected: str, timeout_s: float | None = None) -> str:
        deadline = time.monotonic() + (self.timeout_s if timeout_s is None else timeout_s)
        try:
            while time.monotonic() < deadline:
                self._serial.timeout = max(0.001, deadline - time.monotonic())
                raw = self._serial.readline(97)
                if not raw.endswith(b"\n"):
                    continue
                response = raw.decode("ascii", errors="replace").strip()
                if response == expected:
                    return response
                if response.split(" ", 1)[0] != expected.split(" ", 1)[0]:
                    continue
                if response.startswith(expected.split(" ", 1)[0] + " NACK "):
                    raise RuntimeError(response)
                raise ConnectionError(f"Unexpected UART response: {response!r}")
            raise TimeoutError(f"No UART response: {expected}")
        finally:
            self._serial.timeout = self.timeout_s

