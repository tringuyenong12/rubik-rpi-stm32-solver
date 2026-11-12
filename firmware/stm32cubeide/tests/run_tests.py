"""Run host tests with GCC; no STM32 hardware required."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--uart-only", action="store_true")
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="rubik-uart-tests-") as folder:
    for name, source in (("uart_handle", "App/UART_Handle/UART_Handle.c"),
                         ("rubik_moves", "Hardware/Rubik_Control/Rubik_Control.c")):
        if args.uart_only and name != "uart_handle":
            continue
        output = str(Path(folder) / (name + ".exe"))
        sources = [source]
        if name == "uart_handle":
            sources.append("App/rubik_protocol.c")
            sources.append("Hardware/Servo_Control/Servo_Control.c")
        subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-Itests/host", "-ICore/Inc", "-IApp/UART_Handle", "-IHardware/Rubik_Control",
                        "tests/test_" + name + ".c", *sources, "-o", output], cwd=root, check=True)
        subprocess.run([output], check=True, timeout=15)
