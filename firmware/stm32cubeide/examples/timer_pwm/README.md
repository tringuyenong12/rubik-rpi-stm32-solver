# STM32CubeIDE Firmware

Thư mục này được thiết kế cho workflow STM32CubeIDE/CubeMX.

## Cách Dùng

1. Mở STM32CubeIDE.
2. Tạo project mới, ví dụ `RubikServoController`.
3. Chọn đúng MCU/board đang dùng.
4. Cấu hình peripheral theo [docs/CUBEIDE_SETUP.md](../../../../docs/CUBEIDE_SETUP.md).
5. Copy thư mục `App/` vào project CubeIDE.
6. Trong `Core/Src/main.c`, chèn các call theo `Core_Src_main_user_snippet.c`.
7. Build, flash bằng ST-Link, mở Serial Monitor 115200 baud.

## Vì Sao Tách `App/`

CubeMX có thể regenerate `Core/Src/main.c` và các file init. Code riêng của robot nên nằm ngoài vùng generated code:

- `App/rubik_protocol.*`: parser lệnh UART.
- `App/servo_controller.*`: điều khiển servo và mapping action.

Khi regenerate code, chỉ cần giữ lại include/call trong các block `USER CODE`.

## Lệnh UART Hỗ Trợ

```text
#1 RUBIK PING
#2 RUBIK HOME
#3 RUBIK SERVO <channel> <pulse_us> <duration_ms>
#4 RUBIK MOVE <face> <turns> <duration_ms>
#5 RUBIK ACTUATOR <role> <target> <duration_ms>
#6 RUBIK CLAMP <role> <open|close>
#7 RUBIK TURN <face> <turns> <duration_ms>
#8 RUBIK SCAN_POSE <face>
#9 RUBIK STOP
```

`MOVE` và `SERVO` dùng để bring-up/debug. Khi tích hợp theo bản vẽ cơ khí, ưu tiên dùng `ACTUATOR`, `CLAMP`, `TURN` và `SCAN_POSE`.
