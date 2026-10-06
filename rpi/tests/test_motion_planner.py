from rubik_robot.motion.planner import MotionPlanner


def test_plan_parses_standard_moves():
    actions = MotionPlanner(default_duration_ms=100).plan("R U' F2")

    assert [action.to_wire() for action in actions] == [
        "MOVE R 1 100",
        "MOVE U -1 100",
        "MOVE F 2 200",
    ]


def test_plan_can_emit_turn_commands_for_mechanical_protocol():
    actions = MotionPlanner(default_duration_ms=100, face_turn_command="TURN").plan("R U' F2")

    assert [action.to_wire() for action in actions] == [
        "TURN R 1 100",
        "TURN U -1 100",
        "TURN F 2 200",
    ]

