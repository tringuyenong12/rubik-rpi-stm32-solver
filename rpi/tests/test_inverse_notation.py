import unittest

from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.protocol import Command


class InverseNotationTests(unittest.TestCase):
    def test_both_formula_spellings_produce_same_wire_frames(self):
        for operation in ("MOVE", "TURN"):
            planner = MotionPlanner(face_turn_command=operation)
            for face in "URFDLB":
                original = planner.plan(face + "'")[0]
                renamed = planner.plan(face + "_")[0]
                self.assertEqual(original, renamed)
                self.assertEqual(original.command.turns, -1)
                self.assertEqual(original.command.to_wire("567"),
                                 f"#567 RUBIK {operation} {face}_ -1 450")

    def test_short_command(self):
        self.assertEqual(Command("MOVE", ("L'",)).to_wire("567"),
                         "#567 RUBIK MOVE L_")
        self.assertEqual(Command("MOVE", ("R_",)).to_wire("568"),
                         "#568 RUBIK MOVE R_")

    def test_conflicting_direction_rejected(self):
        with self.assertRaises(ValueError):
            Command("MOVE", ("L_", 1, 450)).to_wire("567")

    def test_forward_and_half_turn_unchanged(self):
        actions = MotionPlanner().plan("R L2")
        self.assertEqual([a.to_wire() for a in actions],
                         ["MOVE R 1 450", "MOVE L 2 900"])


if __name__ == "__main__":
    unittest.main()
