import sys
from types import SimpleNamespace

import unittest
from unittest.mock import patch

from rubik_robot.protocol import Command
from rubik_robot.transport.serial_link import SerialLink


class FakeSerial:
    def __init__(self, mode="ok"):
        self.mode = mode
        self.lines = []
        self.writes = []
        self.closed = False

    def reset_input_buffer(self):
        self.lines.clear()

    def write(self, frame):
        self.writes.append(frame)
        tag, function, operation, *args = frame.strip().split()
        assert function in {b"RUBIK", b"CALIB"}
        if self.mode == "ok":
            self.lines.extend([b"#old ACK\n", tag + b" ACK\n"])
            if operation in {b"HOME", b"MOVE", b"servo"}:
                self.lines.append(tag + b" DONE\n")
        elif self.mode == "wrong":
            self.lines.append(b"#wrong ACK\n")
        elif self.mode == "nack":
            self.lines.append(tag + b" NACK BAD_CMD unknown\n")
        return len(frame)

    def readline(self, size):
        return self.lines.pop(0) if self.lines else b""

    def close(self):
        self.closed = True


class SerialLinkTests(unittest.TestCase):
    def install(self, mode="ok"):
        port = FakeSerial(mode)
        mock = patch.dict(sys.modules, {"serial": SimpleNamespace(Serial=lambda *a, **kw: port)})
        mock.start()
        self.addCleanup(mock.stop)
        return port

    def test_handshake_and_complete_command(self):
        port = self.install()
        with SerialLink("test", timeout_s=0.01) as link:
            self.assertTrue(link.connected)
            self.assertEqual(link.request(Command("HOME"), tag="567"), "#567 DONE")
            self.assertTrue(link.check_connection())
            self.assertFalse(port.lines)
        self.assertFalse(link.connected)
        self.assertTrue(port.closed)

    def test_handshake_failure_closes_port(self):
        for mode in ("silent", "wrong"):
            with self.subTest(mode=mode):
                port = self.install(mode)
                link = SerialLink("test", timeout_s=0.001)
                with self.assertRaises(ConnectionError):
                    link.open()
                self.assertEqual(len(port.writes), 3)
                self.assertTrue(port.closed)
                self.assertFalse(link.connected)
                with self.assertRaises(RuntimeError):
                    link.request(Command("HOME"))

    def test_disconnect_invalidates_connection(self):
        port = self.install()
        link = SerialLink("test", timeout_s=0.001)
        link.open()
        port.mode = "silent"
        self.assertFalse(link.check_connection())
        self.assertFalse(link.connected)
        self.assertTrue(port.closed)

    def test_exact_user_frame_and_duplicate_tag(self):
        port = self.install()
        with SerialLink("test", timeout_s=0.01) as link:
            self.assertEqual(link.request(Command("MOVE", ("L",)), tag="567"), "#567 DONE")
            self.assertEqual(port.writes[-1], b"#567 RUBIK MOVE L\n")
            with self.assertRaises(ValueError):
                link.request(Command("MOVE", ("L",)), tag="567")

    def test_nack_is_not_success(self):
        port = self.install()
        with SerialLink("test", timeout_s=0.01) as link:
            port.mode = "nack"
            with self.assertRaisesRegex(RuntimeError, "NACK"):
                link.request(Command("UNKNOWN"), tag="err1")

    def test_invalid_tag(self):
        for tag in ("", "#12", "a b", "a\nHOME", "a" * 33):
            with self.assertRaises(ValueError):
                Command("PING").to_wire(tag)

    def test_port_open_failure(self):
        def fail(*args, **kwargs):
            raise OSError("port unavailable")
        with patch.dict(sys.modules, {"serial": SimpleNamespace(Serial=fail)}):
            with self.assertRaisesRegex(ConnectionError, "port unavailable"):
                SerialLink("missing").open()

    def test_custom_function_waits_for_done(self):
        port = self.install()
        with SerialLink("test", timeout_s=0.01) as link:
            command = Command("servo", (0, 1500, 300), function="CALIB")
            self.assertEqual(link.request(command, tag="578"), "#578 DONE")
            self.assertEqual(port.writes[-1], b"#578 CALIB servo 0 1500 300\n")
            self.assertFalse(port.lines)

    def test_custom_ack_only_operation(self):
        self.install()
        with SerialLink("test", timeout_s=0.01) as link:
            command = Command("status", function="CALIB", wait_done=False)
            self.assertEqual(link.request(command, tag="579"), "#579 ACK")

    def test_motion_waits_beyond_ack_timeout(self):
        port = self.install()
        elapsed = [0.0]
        read = port.readline

        def delayed_read(size):
            if port.lines and port.lines[0].endswith(b" DONE\n"):
                elapsed[0] += 1.0
                if elapsed[0] < 3.0:
                    return b""
            return read(size)

        port.readline = delayed_read
        with patch("rubik_robot.transport.serial_link.time.monotonic", side_effect=lambda: elapsed[0]):
            with SerialLink("test", timeout_s=0.1, motion_timeout_s=5.0) as link:
                self.assertEqual(link.request(Command("HOME"), tag="slow"), "#slow DONE")
                self.assertEqual(port.timeout, 0.1)

    def test_motion_timeout_closes_connection(self):
        port = self.install()
        elapsed = [0.0]
        read = port.readline

        def missing_done(size):
            if port.lines and port.lines[0].endswith(b" DONE\n"):
                port.lines.clear()
            if not port.lines:
                elapsed[0] += 1.0
                return b""
            return read(size)

        port.readline = missing_done
        with patch("rubik_robot.transport.serial_link.time.monotonic", side_effect=lambda: elapsed[0]):
            with SerialLink("test", timeout_s=0.1, motion_timeout_s=5.0) as link:
                with self.assertRaises(TimeoutError):
                    link.request(Command("HOME"), tag="slow")
                self.assertFalse(link.connected)
                self.assertTrue(port.closed)

    def test_custom_function_does_not_apply_rubik_notation(self):
        command = Command("MOVE", ("L'",), function="OTHER")
        self.assertEqual(command.to_wire("580"), "#580 OTHER MOVE L'")

    def test_invalid_function_or_operation(self):
        for value in ("", "a b", "x\nHOME", "a" * 25, "1name"):
            for command in (Command("servo", function=value), Command(value)):
                with self.assertRaises(ValueError):
                    command.to_wire("581")


if __name__ == "__main__":
    unittest.main()
