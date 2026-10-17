# STM32CubeIDE Firmware

Thư mục này được thiết kế cho workflow STM32CubeIDE/CubeMX.

## Cách Dùng

1. Mở STM32CubeIDE.
2. Tạo project mới, ví dụ `RubikServoController`.
3. Chọn đúng MCU/board đang dùng.
4. Cấu hình peripheral theo [docs/CUBEIDE_SETUP.md](../../docs/CUBEIDE_SETUP.md).
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

Trước khi bật PWM, cấu hình từng timer/kênh và profile bằng số đo thực tế theo
[hướng dẫn servo](App/SERVO_CONTROLLER_GUIDE.md). Chưa có profile thì snippet báo
`ERR CONFIG servo_not_ready`; không tự đưa servo về 1500 µs.

`SERVO`, `ACTUATOR`, `CLAMP` dùng các profile đã cấu hình. `MOVE`, `TURN` và
`SCAN_POSE` hiện trả `ERR UNSUPPORTED` vì chưa có sequence cơ khí. `STOP` chỉ khóa
lệnh mới và giữ PWM cuối, không phải dừng khẩn cấp.

Kiểm thử driver với HAL giả lập từ thư mục gốc: `python firmware/tests/run_tests.py`.
