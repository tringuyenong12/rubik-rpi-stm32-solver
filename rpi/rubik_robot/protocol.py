from __future__ import annotations

from dataclasses import dataclass, field
import re


@dataclass(frozen=True)
class Command:
    name: str
    args: tuple[object, ...] = ()
    function: str = field(default="RUBIK", kw_only=True)
    wait_done: bool | None = field(default=None, kw_only=True)

    def to_wire(self, tag: str | None = None) -> str:
        for value in (self.function, self.name):
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,23}", value):
                raise ValueError("Function and operation must be identifiers of 1-24 ASCII characters")
        if tag is not None:
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", tag):
                raise ValueError("Tag must contain 1-32 letters, digits, underscores or hyphens")
            return f"#{tag} {self.function} {self.to_wire()}"
        if not self.args:
            return self.name
        args = [str(arg) for arg in self.args]
        if self.function == "RUBIK" and self.name in {"MOVE", "TURN"}:
            face = args[0]
            if len(face) == 2 and face[0] in "URFDLB" and face[1] == "'":
                face = face[0] + "_"
            if len(face) == 1 and face in "URFDLB" and len(args) > 1 and args[1] == "-1":
                face += "_"
            if face.endswith("_") and len(args) > 1 and args[1] != "-1":
                raise ValueError("Inverse face suffix requires turns=-1")
            args[0] = face
        return " ".join([self.name, *args])

    @property
    def expects_done(self) -> bool:
        if self.wait_done is not None:
            return self.wait_done
        if self.function == "RUBIK":
            return self.name in {"HOME", "MOVE", "TURN", "SERVO", "ACTUATOR", "CLAMP", "SCAN_POSE"}
        return True


@dataclass(frozen=True)
class MoveCommand(Command):
    face: str = "U"
    turns: int = 1
    duration_ms: int = 450

    def __init__(self, face: str, turns: int, duration_ms: int, command_name: str = "MOVE") -> None:
        if len(face) != 1 or face not in "URFDLB":
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

