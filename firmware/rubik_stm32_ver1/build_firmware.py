"""Build the STM32F411 firmware from source without reusing CubeIDE Debug files."""

import argparse
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gcc", default="arm-none-eabi-gcc", help="ARM GCC executable")
    parser.add_argument("--output", type=Path, required=True, help="Destination .elf")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    target = ["-mcpu=cortex-m4", "-mthumb", "-mfpu=fpv4-sp-d16", "-mfloat-abi=hard"]
    includes = [
        "Core/Inc", "Drivers/STM32F4xx_HAL_Driver/Inc",
        "Drivers/STM32F4xx_HAL_Driver/Inc/Legacy",
        "Drivers/CMSIS/Device/ST/STM32F4xx/Include", "Drivers/CMSIS/Include",
    ]
    sources = [
        source.relative_to(root)
        for pattern in ("Core/Src/*.c", "Core/Startup/*.s", "Hardware/*/*.c",
                        "Drivers/STM32F4xx_HAL_Driver/Src/*.c", "Testing/*.c")
        for source in sorted(root.glob(pattern))
    ]
    with TemporaryDirectory(prefix="rubik-firmware-") as directory:
        objects = []
        for index, source in enumerate(sources):
            obj = str(Path(directory) / f"{index}.o")
            subprocess.run([
                args.gcc, *target, "-std=gnu11", "-g3", "-O0", "-DDEBUG",
                "-DUSE_HAL_DRIVER", "-DSTM32F411xE", "--specs=nano.specs",
                "-ffunction-sections", "-fdata-sections",
                *(f"-I{path}" for path in includes), "-c", str(source), "-o", obj,
            ], cwd=root, check=True)
            objects.append(obj)
        subprocess.run([
            args.gcc, *target, *objects, "-TSTM32F411CEUX_FLASH.ld", "--specs=nosys.specs",
            "--specs=nano.specs", "-Wl,--gc-sections", "-static",
            "-Wl,--start-group", "-lc", "-lm", "-Wl,--end-group", "-o", str(output),
        ], cwd=root, check=True)
    print(f"Built {output}")


if __name__ == "__main__":
    main()
