"""Compile and exercise the servo driver using a fake HAL, without hardware."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

tests = Path(__file__).resolve().parent
firmware = tests.parent
app = firmware / "stm32cubeide" / "App"
compiler = shutil.which(os.environ.get("CC", "gcc"))
if not compiler:
    raise SystemExit("C compiler not found; install GCC or set CC to its path.")
flags = ["-std=c99", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-I", str(tests / "hal_stub"), "-I", str(app)]
with tempfile.TemporaryDirectory(prefix="rubik-servo-tests-") as tmp:
    output = Path(tmp) / "servo_tests.exe"
    subprocess.run([compiler, *flags, str(tests / "test_servo_controller.c"),
                    str(app / "servo_controller.c"), "-o", str(output)], check=True)
    subprocess.run([str(output)], check=True)

    # Assemble the documented insertion blocks into a translation unit.
    snippet = (firmware / "stm32cubeide" / "Core_Src_main_user_snippet.c").read_text(
        encoding="utf-8-sig")
    snippet = snippet.replace("/* USER CODE BEGIN 2 */", """
extern TIM_HandleTypeDef htim2;
extern UART_HandleTypeDef huart1;
int main(void) {
/* USER CODE BEGIN 2 */""")
    snippet = snippet.replace("/* USER CODE END 3 */", "/* USER CODE END 3 */\n}")
    unit = Path(tmp) / "main_snippet.c"
    unit.write_text(snippet, encoding="utf-8")
    subprocess.run([compiler, *flags, "-fsyntax-only", str(unit)], check=True)
    print("PASS: main.c integration snippet compiles without warnings")
