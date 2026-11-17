# Các hàm xoay Rubik qua UART

Module `motion/motion.py` sử dụng
`UART_Command/UART_Command.py::Send_Command_to_STM32()` để gửi lệnh.
Chạy Python từ thư mục `rpi/` (cần cài `pyserial`).

```python
from Rubik_Cube.motion.motion import move_Front, move_Front_, U, R_, move
from Rubik_Cube.UART_Command.UART_Command import UART_Close

try:
    # Mỗi hàm chờ kết quả; dừng chuỗi ngay khi một lệnh thất bại.
    for action in (move_Front, move_Front_, U, R_):
        if not action():
            break
finally:
    UART_Close()
```

| Hàm | Tên ngắn | Lệnh gửi cho tầng UART_Command |
| --- | --- | --- |
| `move_Front()` | `move_F()`, `F()` | `RUBIK MOVE F` |
| `move_Front_()` | `move_F_()`, `F_()` | `RUBIK MOVE F_` |
| `move_Right()` | `move_R()`, `R()` | `RUBIK MOVE R` |
| `move_Right_()` | `move_R_()`, `R_()` | `RUBIK MOVE R_` |
| `move_Back()` | `move_B()`, `B()` | `RUBIK MOVE B` |
| `move_Back_()` | `move_B_()`, `B_()` | `RUBIK MOVE B_` |
| `move_Left()` | `move_L()`, `L()` | `RUBIK MOVE L` |
| `move_Left_()` | `move_L_()`, `L_()` | `RUBIK MOVE L_` |
| `move_Up()` | `move_U()`, `U()` | `RUBIK MOVE U` |
| `move_Up_()` | `move_U_()`, `U_()` | `RUBIK MOVE U_` |
| `move_Down()` | `move_D()`, `D()` | `RUBIK MOVE D` |
| `move_Down_()` | `move_D_()`, `D_()` | `RUBIK MOVE D_` |

Hậu tố `_` biểu thị phép xoay ngược. Có thể dùng hàm chung `move("F")`,
`move("R_")` hoặc `move("U'")`; dấu nháy được đổi sang `_` trước khi gửi.
Lệnh không hợp lệ gây `ValueError` và không gửi UART. Mỗi lần gọi chỉ gửi
một phép xoay; chưa hỗ trợ token `F2` hoặc chuỗi nhiều phép xoay.

Kết quả `True`/`False` được trả nguyên từ tầng UART_Command. Tầng này tự mở
cổng `/dev/serial0`, dùng baudrate 115200, thêm `#ID` và ký tự xuống dòng,
chờ OK/DONE và xử lý ERR. Import module không mở cổng hay gửi lệnh.

## Solver / UART

See [solver UART guide](../../docs/solver_uart.md) for the current protocol,
command mapping, execution scripts, timeouts and firmware limitations.
