from __future__ import annotations

from dataclasses import dataclass

from rubik_robot.protocol import MoveCommand


@dataclass(frozen=True)
class PlannedAction:
    command: MoveCommand
    cost_ms: int

    def to_wire(self) -> str:
        return self.command.to_wire()


class MotionPlanner:
    def __init__(self, default_duration_ms: int = 450, face_turn_command: str = "MOVE") -> None:
        self.default_duration_ms = default_duration_ms
        self.face_turn_command = face_turn_command

    def plan(self, solution: str) -> list[PlannedAction]:
        """Merge adjacent LR/FB turns in either order using firmware pair moves."""
        actions: list[PlannedAction] = []
        moves = [self._parse_move(token) for token in solution.split()]
        index = 0
        while index < len(moves):
            face, turns = moves[index]
            index += 1
            second_face = second_turns = None
            if index < len(moves) and {face, moves[index][0]} in ({"L", "R"}, {"F", "B"}):
                second_face, second_turns = moves[index]
                index += 1
                if face in {"R", "B"}:
                    face, second_face = second_face, face
                    turns, second_turns = second_turns, turns
            duration = self.default_duration_ms * (2 if turns == 2 else 1)
            if second_turns == 2:
                duration = self.default_duration_ms * 2
            actions.append(
                PlannedAction(
                    command=MoveCommand(
                        face=face,
                        turns=turns,
                        duration_ms=duration,
                        command_name=self.face_turn_command,
                        second_face=second_face,
                        second_turns=second_turns,
                    ),
                    cost_ms=duration,
                )
            )
        return actions

    @staticmethod
    def _parse_move(token: str) -> tuple[str, int]:
        if not token:
            raise ValueError("Empty move token")

        face = token[0]
        suffix = token[1:]
        if face not in tuple("URFDLB"):
            raise ValueError(f"Invalid move face: {token}")
        if suffix in {"", "1"}:
            return face, 1
        if suffix in {"'", "3", "_"}:
            return face, -1
        if suffix == "2":
            return face, 2
        raise ValueError(f"Invalid move suffix: {token}")

