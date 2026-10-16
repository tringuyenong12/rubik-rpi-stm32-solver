from __future__ import annotations

from dataclasses import dataclass


# Binary UART command values understood by firmware/stm32cubeide/App/rubik_binary_protocol.*.
# A clockwise move uses the same convention as standard Rubik notation: ``R``;
# counter-clockwise is ``R'`` and a half turn is ``R2``.
MOVE_COMMAND_CODES: dict[tuple[str, int], int] = {
    ("F", 1): 1,
    ("F", -1): 2,
    ("F", 2): 3,
    ("B", 1): 4,
    ("B", -1): 5,
    ("B", 2): 6,
    ("L", 1): 7,
    ("L", -1): 8,
    ("L", 2): 9,
    ("R", 1): 10,
    ("R", -1): 11,
    ("R", 2): 12,
    ("U", 1): 13,
    ("U", -1): 14,
    ("U", 2): 15,
    ("D", 1): 16,
    ("D", -1): 17,
    ("D", 2): 18,
}

STM32_CMD_PING = 0x00
STM32_CMD_FINISH = 0xFF
STM32_CMD_HOME = 0xFE


def move_to_stm32_code(face: str, turns: int) -> int:
    """Convert one standard cube move to its STM32 motion command byte."""
    try:
        return MOVE_COMMAND_CODES[(face, turns)]
    except KeyError as exc:
        raise ValueError(f"Unsupported STM32 move: {face!r} {turns!r}") from exc


def crc8(data: bytes) -> int:
    """CRC-8/ATM (polynomial 0x07, initial value 0) for UART frames."""
    crc = 0
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def encode_stm32_frame(sequence: int, command_code: int) -> bytes:
    """Return ``SOF, sequence, command, CRC8`` for the STM32 binary protocol."""
    if not 0 <= sequence <= 0xFF:
        raise ValueError("UART sequence must fit in one byte")
    if not 0 <= command_code <= 0xFF:
        raise ValueError("UART command code must fit in one byte")
    payload = bytes((sequence, command_code))
    return bytes((0xA5, *payload, crc8(payload)))


@dataclass(frozen=True)
class Command:
    name: str
    args: tuple[object, ...] = ()

    def to_wire(self) -> str:
        if not self.args:
            return self.name
        return " ".join([self.name, *[str(arg) for arg in self.args]])


@dataclass(frozen=True)
class MoveCommand(Command):
    face: str = "U"
    turns: int = 1
    duration_ms: int = 450

    def __init__(self, face: str, turns: int, duration_ms: int, command_name: str = "MOVE") -> None:
        if face not in "URFDLB":
            raise ValueError(f"Invalid face: {face}")
        if turns not in {-1, 1, 2}:
            raise ValueError(f"Invalid turns: {turns}")
        if command_name not in {"MOVE", "TURN"}:
            raise ValueError(f"Invalid face turn command name: {command_name}")
        object.__setattr__(self, "name", command_name)
        object.__setattr__(self, "args", (face, turns, duration_ms))
        object.__setattr__(self, "face", face)
        object.__setattr__(self, "turns", turns)
        object.__setattr__(self, "duration_ms", duration_ms)

    def to_stm32_code(self) -> int:
        return move_to_stm32_code(self.face, self.turns)

