"""Generate reproducible scramble plans from a solved cube."""

from dataclasses import dataclass
import random

from rubik_robot.motion.planner import MotionPlanner, PlannedAction
from twophase.cubie import CubieCube, basicMoveCube


LEVELS = {'easy': 5, 'medium': 12, 'hard': 22}
FACES = 'URFDLB'
AXES = {'U': 'UD', 'D': 'UD', 'R': 'RL', 'L': 'RL', 'F': 'FB', 'B': 'FB'}


@dataclass(frozen=True)
class ScramblePlan:
    """A solved-cube scramble, its resulting state and ordered UART actions."""

    level: str
    moves: tuple[str, ...]
    cube: str
    actions: tuple[PlannedAction, ...]

    def uart_text(self) -> str:
        """Input: this plan. Output: newline-terminated UART frames in scramble order."""
        return ''.join(action.to_wire() + '\n' for action in self.actions)


def create_scramble(level: str, seed: int | None = None, duration_ms: int = 450,
                    command_name: str = 'TURN') -> ScramblePlan:
    """Input: level, optional seed and UART settings. Output: a plan starting from solved."""
    if level not in LEVELS:
        raise ValueError('Choose easy, medium or hard')
    if duration_ms <= 0:
        raise ValueError('Duration must be positive')
    generator = random.Random(seed)
    cube = CubieCube()
    moves = []
    previous_axis = None
    for _ in range(LEVELS[level]):
        face = generator.choice([face for face in FACES if AXES[face] != previous_axis])
        suffix = generator.choice(('', "'", '2'))
        moves.append(face + suffix)
        turns = {'': 1, "'": 3, '2': 2}[suffix]
        for _ in range(turns):
            cube.multiply(basicMoveCube[FACES.index(face)])
        previous_axis = AXES[face]
    planner = MotionPlanner(default_duration_ms=duration_ms, face_turn_command=command_name)
    actions = tuple(planner.plan(' '.join(moves)))
    return ScramblePlan(level, tuple(moves), cube.to_facelet_cube().to_string(), actions)
