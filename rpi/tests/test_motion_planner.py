import unittest

from rubik_robot.motion.planner import MotionPlanner


class TestMotionPlanner(unittest.TestCase):
    def test_plan_parses_standard_moves(self):
        actions = MotionPlanner(default_duration_ms=100).plan("R U' F2")
        self.assertEqual(
            [action.to_wire() for action in actions],
            [
                "MOVE R 1 100",
                "MOVE U -1 100",
                "MOVE F 2 200",
            ],
        )

    def test_plan_parses_twophase_numbered_moves(self):
        actions = MotionPlanner(default_duration_ms=100, face_turn_command="TURN").plan("R1 U3 F2")
        self.assertEqual(
            [action.to_wire() for action in actions],
            [
                "TURN R 1 100",
                "TURN U -1 100",
                "TURN F 2 200",
            ],
        )

    def test_plan_can_emit_turn_commands_for_mechanical_protocol(self):
        actions = MotionPlanner(default_duration_ms=100, face_turn_command="TURN").plan("R U' F2")
        self.assertEqual(
            [action.to_wire() for action in actions],
            [
                "TURN R 1 100",
                "TURN U -1 100",
                "TURN F 2 200",
            ],
        )


if __name__ == "__main__":
    unittest.main()

