from rubik_robot.protocol import MoveCommand, crc8, encode_stm32_frame, move_to_stm32_code


def test_move_bytes_match_the_eight_servo_firmware_mapping():
    assert move_to_stm32_code("F", 1) == 1
    assert move_to_stm32_code("R", -1) == 11
    assert move_to_stm32_code("U", 2) == 15
    assert move_to_stm32_code("D", -1) == 17
    assert MoveCommand("L", 2, 900).to_stm32_code() == 9


def test_binary_frame_has_sof_sequence_command_and_crc8():
    frame = encode_stm32_frame(1, 11)
    assert frame == bytes((0xA5, 0x01, 0x0B, 0x24))
    assert crc8(frame[1:3]) == frame[3]
