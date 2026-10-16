from __future__ import annotations

import time
from dataclasses import dataclass

from rubik_robot.protocol import (
    STM32_CMD_FINISH,
    STM32_CMD_HOME,
    STM32_CMD_PING,
    Command,
    MoveCommand,
    crc8,
    encode_stm32_frame,
)


STM32_RESPONSE_SOF = 0x5A
STM32_STATUS_ACK = 0x06
STM32_STATUS_DONE = 0x44
STM32_STATUS_ERROR = 0x15
STM32_STATUS_BUSY = 0x42


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


@dataclass
class Stm32BinaryLink:
    """Reliable binary UART link for the eight-servo STM32 Rubik firmware.

    Each command is sent as ``A5 sequence command CRC8``.  The STM32 echoes
    ``5A sequence status CRC8`` first with ACK and then with DONE.  Retrying
    uses the *same* sequence number, allowing the firmware to acknowledge a
    lost response without executing a physical move twice.
    """

    port: str
    baudrate: int = 115200
    ack_timeout_s: float = 0.8
    direct_move_timeout_s: float = 3.0
    reorient_move_timeout_s: float = 9.0
    retries: int = 3

    def __post_init__(self) -> None:
        self._serial = None
        self._sequence = 0
        self._rx_buffer = bytearray()

    def __enter__(self) -> "Stm32BinaryLink":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        import serial

        # A short per-read timeout lets the response parser enforce its own
        # deadline while leaving the CPU idle between incoming bytes.
        self._serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=min(0.1, self.ack_timeout_s),
            write_timeout=1.0,
        )
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def ping(self) -> str:
        self.request_code(STM32_CMD_PING, timeout_s=1.5)
        return "DONE PING"

    def home(self) -> str:
        self.request_code(STM32_CMD_HOME, timeout_s=3.0)
        return "DONE HOME"

    def finish(self) -> str:
        self.request_code(STM32_CMD_FINISH, timeout_s=1.5)
        return "DONE FINISH"

    def request_move(self, command: MoveCommand) -> str:
        return self.request_code(
            command.to_stm32_code(),
            timeout_s=self._move_timeout(command),
        )

    def request_code(self, command_code: int, *, timeout_s: float) -> str:
        if self._serial is None:
            raise RuntimeError("Stm32BinaryLink is not open")
        if timeout_s <= 0:
            raise ValueError("timeout_s must be positive")

        sequence = self._next_sequence()
        frame = encode_stm32_frame(sequence, command_code)

        # The command may already have reached the STM32 when an ACK is lost.
        # Therefore do not allocate a new sequence number on retry.
        acknowledged = False
        for _ in range(self.retries + 1):
            self._write(frame)
            status = self._wait_for_response(sequence, self.ack_timeout_s)
            if status == STM32_STATUS_DONE:
                return "DONE"
            if status == STM32_STATUS_ACK:
                acknowledged = True
                break
            self._raise_for_status(status, sequence)

        # Even without ACK, the command might now be running.  Wait for DONE
        # before declaring a failure so a later retry cannot double-turn cube.
        status = self._wait_for_response(sequence, timeout_s)
        if status == STM32_STATUS_DONE:
            return "DONE"
        self._raise_for_status(status, sequence)

        if acknowledged:
            # A final duplicate frame asks firmware to replay cached DONE if
            # the original completion byte was lost.
            self._write(frame)
            status = self._wait_for_response(sequence, self.ack_timeout_s)
            if status == STM32_STATUS_DONE:
                return "DONE"
            self._raise_for_status(status, sequence)

        raise TimeoutError(
            f"STM32 did not acknowledge command 0x{command_code:02X} "
            f"(sequence {sequence})"
        )

    def _move_timeout(self, command: MoveCommand) -> float:
        # F/B/L/R use one rotate_face sequence.  U/D additionally flip the
        # cube before and after the face turn, so they require a longer limit.
        base = (
            self.reorient_move_timeout_s
            if command.face in {"U", "D"}
            else self.direct_move_timeout_s
        )
        return base * (1.25 if command.turns == 2 else 1.0)

    def _next_sequence(self) -> int:
        self._sequence = (self._sequence % 255) + 1
        return self._sequence

    def _write(self, frame: bytes) -> None:
        assert self._serial is not None
        written = self._serial.write(frame)
        if written != len(frame):
            raise RuntimeError(f"Short UART write: {written}/{len(frame)} bytes")
        self._serial.flush()

    def _wait_for_response(self, sequence: int, timeout_s: float) -> int | None:
        assert self._serial is not None
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            chunk = self._serial.read(self._serial.in_waiting or 1)
            if chunk:
                self._rx_buffer.extend(chunk)

            while True:
                try:
                    sof_index = self._rx_buffer.index(STM32_RESPONSE_SOF)
                except ValueError:
                    self._rx_buffer.clear()
                    break

                if sof_index:
                    del self._rx_buffer[:sof_index]
                if len(self._rx_buffer) < 4:
                    break

                _, received_sequence, status, received_crc = self._rx_buffer[:4]
                del self._rx_buffer[:4]
                if crc8(bytes((received_sequence, status))) != received_crc:
                    continue
                if received_sequence == sequence:
                    return status
        return None

    @staticmethod
    def _raise_for_status(status: int | None, sequence: int) -> None:
        if status is None:
            return
        if status == STM32_STATUS_ERROR:
            raise RuntimeError(f"STM32 rejected command (sequence {sequence})")
        if status == STM32_STATUS_BUSY:
            raise RuntimeError(f"STM32 is busy (sequence {sequence})")
        if status != STM32_STATUS_ACK:
            raise RuntimeError(f"Unexpected STM32 status 0x{status:02X} (sequence {sequence})")

