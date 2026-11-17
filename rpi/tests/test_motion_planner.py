import unittest
from itertools import product

from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.vision.solve_guide import apply_move


class TestMotionPlanner(unittest.TestCase):
    def test_opposite_pairs_preserve_cube_for_all_directions_and_orders(self):
        for pair, suffixes, reverse in product(('LR', 'FB'), product(('', "'", '2'), repeat=2), (False, True)):
            moves = [face + suffix for face, suffix in zip(pair, suffixes)]
            if reverse:
                moves.reverse()
            with self.subTest(moves=moves):
                action, = MotionPlanner(default_duration_ms=100).plan(' '.join(moves))
                expected = SOLVED_CUBE
                for move in moves:
                    expected = apply_move(expected, move)
                actual = SOLVED_CUBE
                for token in action.command.tokens:
                    for index, face in enumerate(token):
                        if face in 'URFDLB':
                            inverse = token[index + 1:index + 2] == '_'
                            actual = apply_move(actual, face + ("'" if inverse else ''))
                self.assertEqual(actual, expected)
                self.assertEqual(len(action.command.tokens), 2 if '2' in suffixes else 1)
                self.assertEqual(action.cost_ms, 200 if '2' in suffixes else 100)

    def test_pairs_emit_canonical_firmware_tokens(self):
        actions = MotionPlanner().plan("R' L B F' L2 R2 L2 R F B2")
        self.assertEqual([action.command.tokens for action in actions],
                         [('LR_',), ('F_B',), ('LR', 'LR'), ('LR', 'L'), ('FB', 'B')])

    def test_does_not_cross_intervening_moves_or_pair_unsupported_faces(self):
        actions = MotionPlanner().plan('L F R U D R R')
        self.assertEqual([action.command.tokens for action in actions],
                         [('L',), ('F',), ('R',), ('U',), ('D',), ('R',), ('R',)])

    def test_plan_parses_standard_moves(self):
        actions = MotionPlanner(default_duration_ms=100).plan("R U' F2")
        self.assertEqual(
            [action.to_wire() for action in actions],
            [
                "RUBIK MOVE R",
                "RUBIK MOVE U_",
                "RUBIK MOVE F\nRUBIK MOVE F",
            ],
        )

    def test_plan_parses_twophase_numbered_moves(self):
        actions = MotionPlanner(default_duration_ms=100, face_turn_command="TURN").plan("R1 U3 F2")
        self.assertEqual(
            [action.to_wire() for action in actions],
            [
                "RUBIK MOVE R",
                "RUBIK MOVE U_",
                "RUBIK MOVE F\nRUBIK MOVE F",
            ],
        )

    def test_legacy_turn_option_emits_new_protocol(self):
        actions = MotionPlanner(default_duration_ms=100, face_turn_command="TURN").plan("R U' F2")
        self.assertEqual(
            [action.to_wire() for action in actions],
            [
                "RUBIK MOVE R",
                "RUBIK MOVE U_",
                "RUBIK MOVE F\nRUBIK MOVE F",
            ],
        )


if __name__ == "__main__":
    unittest.main()

