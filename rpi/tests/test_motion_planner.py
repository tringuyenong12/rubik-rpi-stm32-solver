import unittest

from rubik_robot.motion.planner import MotionPlanner


class TestMotionPlanner(unittest.TestCase):
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

