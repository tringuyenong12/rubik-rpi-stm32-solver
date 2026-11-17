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
    second_face: str | None = None
    second_turns: int | None = None

    def __init__(self, face: str, turns: int, duration_ms: int = 450,
                 command_name: str = "MOVE", *, second_face: str | None = None,
                 second_turns: int | None = None) -> None:
        if face not in tuple("URFDLB"):
            raise ValueError(f"Invalid face: {face}")
        if turns not in {-1, 1, 2}:
            raise ValueError(f"Invalid turns: {turns}")
        if command_name not in {"MOVE", "TURN"}:
            raise ValueError(f"Invalid face turn command name: {command_name}")
        if second_face is None:
            if second_turns is not None:
                raise ValueError("Second turns requires a second face")
        elif face + second_face not in {"LR", "FB"} or second_turns not in {-1, 1, 2}:
            raise ValueError("Expected a canonical LR or FB pair with valid turns")
        # Accept the old option for Python callers, but always emit RUBIK MOVE.
        object.__setattr__(self, "name", "MOVE")
        object.__setattr__(self, "args", (face, turns))
        object.__setattr__(self, "face", face)
        object.__setattr__(self, "turns", turns)
        object.__setattr__(self, "duration_ms", duration_ms)
        object.__setattr__(self, "second_face", second_face)
        object.__setattr__(self, "second_turns", second_turns)

    @property
    def moves(self) -> tuple[tuple[str, int], ...]:
        """Original face turns, for cube validation and progress displays."""
        first = ((self.face, self.turns),)
        return first if self.second_face is None else first + ((self.second_face, self.second_turns),)

    @property
    def tokens(self) -> tuple[str, ...]:
        quarters = [
            (face + ("_" if turns == -1 else ""), 2 if turns == 2 else 1)
            for face, turns in self.moves
        ]
        return tuple(
            "".join(token for token, count in quarters if index < count)
            for index in range(max(count for _, count in quarters))
        )

    def bodies(self) -> tuple[str, ...]:
        return tuple(f"RUBIK MOVE {token}" for token in self.tokens)
