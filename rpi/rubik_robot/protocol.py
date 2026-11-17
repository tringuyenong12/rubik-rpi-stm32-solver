from __future__ import annotations

from dataclasses import dataclass


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

