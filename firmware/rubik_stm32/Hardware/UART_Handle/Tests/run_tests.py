"""Test UART with real Servo_Control, then with real Rubik_Control as well."""
from pathlib import Path
import subprocess
import tempfile

folder = Path(__file__).resolve().parent
uart = folder.parent
root = uart.parents[1]
sources = [str(p) for p in sorted(uart.glob("*.c"))]
sources.append(str(root / "Hardware/Servo_Control/Servo_Control.c"))
with tempfile.TemporaryDirectory(prefix="uart-command-tests-") as temporary:
    for real_rubik in (False, True):
        executable = str(Path(temporary) / ("uart_real.exe" if real_rubik else "uart_mock.exe"))
        extra = (["-DUART_TEST_REAL_RUBIK", str(root / "Hardware/Rubik_Control/Rubik_Control.c")]
                 if real_rubik else [])
        subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-I" + str(folder / "host"), "-I" + str(uart),
                        "-x", "c", str(folder / "test_uart.inc"), "-x", "none",
                        *sources, *extra, "-o", executable], check=True)
        subprocess.run([executable], check=True)
