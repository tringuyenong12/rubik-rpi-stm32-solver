# STM32CubeIDE Firmware

Thu muc nay duoc thiet ke cho workflow STM32CubeIDE/CubeMX.

## Cach Dung

1. Mo STM32CubeIDE.
2. Tao project moi, vi du `RubikServoController`.
3. Chon dung MCU/board dang dung.
4. Cau hinh peripheral theo [docs/CUBEIDE_SETUP.md](../../docs/CUBEIDE_SETUP.md).
5. Copy thu muc `App/` vao project CubeIDE.
6. Trong `Core/Src/main.c`, chen cac call theo `Core_Src_main_user_snippet.c`.
7. Build, flash bang ST-Link, mo Serial Monitor 115200 baud.

## Vi Sao Tach `App/`

CubeMX co the regenerate `Core/Src/main.c` va cac file init. Code rieng cua robot nen nam ngoai vung generated code:

- `App/rubik_protocol.*`: parser lenh UART.
- `App/servo_controller.*`: dieu khien servo va mapping action.

Khi regenerate code, chi can giu lai include/call trong cac block `USER CODE`.

## Lenh UART Ho Tro

```text
PING
HOME
SERVO <channel> <pulse_us> <duration_ms>
MOVE <face> <turns> <duration_ms>
ACTUATOR <role> <target> <duration_ms>
CLAMP <role> <open|close>
TURN <face> <turns> <duration_ms>
SCAN_POSE <face>
STOP
```

`MOVE` va `SERVO` dung de bring-up/debug. Khi tich hop theo ban ve co khi, uu tien dung `ACTUATOR`, `CLAMP`, `TURN` va `SCAN_POSE`.

