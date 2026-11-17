"""Logical actions and STM32 command bodies; UART_Command adds IDs/newlines."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str
    args: tuple[object, ...] = ()

    def bodies(self) -> tuple[str, ...]:
        if self.name in {"PING", "RESET"} and not self.args:
            return (f"RUBIK {self.name}",)
        return (" ".join((self.name, *(str(arg) for arg in self.args))),)

    def to_wire(self) -> str:
        return "\n".join(self.bodies())


@dataclass(frozen=True)
class MoveCommand(Command):
    face: str = "U"
    turns: int = 1
    duration_ms: int = 450  # Estimate only; STM32 controls servo timing.

    def __init__(self, face: str, turns: int, duration_ms: int = 450,
                 command_name: str = "MOVE") -> None:
        if face not in tuple("URFDLB"):
            raise ValueError(f"Invalid face: {face}")
        if turns not in {-1, 1, 2}:
            raise ValueError(f"Invalid turns: {turns}")
        if command_name not in {"MOVE", "TURN"}:
            raise ValueError(f"Invalid face turn command name: {command_name}")
        # Accept the old option for Python callers, but always emit RUBIK MOVE.
        object.__setattr__(self, "name", "MOVE")
        object.__setattr__(self, "args", (face, turns))
        object.__setattr__(self, "face", face)
        object.__setattr__(self, "turns", turns)
        object.__setattr__(self, "duration_ms", duration_ms)

    @property
    def tokens(self) -> tuple[str, ...]:
        token = self.face + ("_" if self.turns == -1 else "")
        return (token,) * (2 if self.turns == 2 else 1)

    def bodies(self) -> tuple[str, ...]:
        return tuple(f"RUBIK MOVE {token}" for token in self.tokens)
