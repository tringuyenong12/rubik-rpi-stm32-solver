"""Run host tests with GCC; no STM32 hardware required."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("--uart-only", action="store_true")
parser.add_argument("--project", type=Path,
                    help="Test another project copy, e.g. the converted VS Code project")
args = parser.parse_args()

root = Path(__file__).resolve().parents[1]
project = args.project.resolve() if args.project else root
with tempfile.TemporaryDirectory(prefix="rubik-uart-tests-") as folder:
    for name, source in (("uart_handle", "App/UART_Handle/UART_Handle.c"),
                         ("rubik_moves", "Hardware/Rubik_Control/Rubik_Control.c")):
        if args.uart_only and name != "uart_handle":
            continue
        output = str(Path(folder) / (name + ".exe"))
        sources = [str(project / source)]
        if name == "uart_handle":
            sources.append(str(project / "App/rubik_protocol.c"))
            sources.append(str(project / "Hardware/Servo_Control/Servo_Control.c"))
        subprocess.run(["gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-Itests/host", "-I" + str(project / "Core/Inc"),
                        "-I" + str(project / "App/UART_Handle"),
                        "-I" + str(project / "Hardware/Rubik_Control"),
                        "tests/test_" + name + ".c", *sources, "-o", output], cwd=root, check=True)
        subprocess.run([output], check=True, timeout=15)
