"""Compile the UART command handlers with host servo/UART fakes."""
from pathlib import Path
import argparse
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--control-only", action="store_true")
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix="rubik-command-tests-") as folder:
    Path(folder, "main.h").write_text("/* Host test: no board peripherals. */\n")
    shim = Path(folder, "delay.h")
    shim.write_text("#include <stdint.h>\nvoid HAL_Delay(uint32_t ms);\n")
    output = str(Path(folder, "commands.exe"))
    sources = ["Hardware/UART_Handle/Control_Command.c"]
    if args.control_only:
        sources.append("-DCONTROL_ONLY")
    else:
        sources += ["Hardware/UART_Handle/Rubik_Command.c", "Hardware/Rubik_Control/Rubik_Control.c"]
    subprocess.run([
        "gcc", "-std=c11", "-Wall", "-Wextra", "-Werror",
        "-include", str(shim),
        "-I" + folder, "-Itests/host", "-IHardware/UART_Handle",
        "tests/test_commands.c", *sources, "-o", output,
    ], cwd=root, check=True)
    subprocess.run([output], check=True)
