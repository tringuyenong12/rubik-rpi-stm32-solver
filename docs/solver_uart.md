# Chạy solver với UART STM32 mới

Luồng thực thi: solver → MotionPlanner → SerialLink → các hàm trong
`Rubik_Cube/motion/motion.py` → Send_Command_to_STM32 → UARTSession → STM32.
Phần calibration giữ nguyên.

Firmware hiện nhận `#ID RUBIK MOVE F\n`, trả `>#ID OK`, rồi `>#ID DONE`
hoặc `>#ID ERR ...`. Python chờ DONE đúng ID trước khi gửi lệnh tiếp theo.
`PING` gửi thành `RUBIK PING`; khởi tạo cơ cấu dùng `RUBIK RESET`.

## Cách chạy

Chạy từ thư mục gốc repo, dùng Python có các thư viện trong `rpi/requirements.txt`:

```sh
# Xem trước lời giải, chưa mở UART (thay bằng chuỗi 54 ô thật):
python scripts/run_solver.py --cube "CHUOI_54_O_URFDLB"

# Giải và gửi:
python scripts/run_solver.py --cube "CHUOI_54_O_URFDLB" --port /dev/serial0

# Đọc JSON có cube và solution, kiểm tra rồi gửi:
python scripts/run_solver.py --input solution.json --port /dev/serial0 --timeout 30

# Xuất nội dung lệnh, không mở UART:
python scripts/run_solver.py --input solution.json --output commands.txt
```

Windows có thể dùng `--port COM3`. JSON cần trường `cube` (54 ký tự theo thứ tự
URFDLB); `solution` là công thức tùy chọn. Không có solution thì chạy solver.
Python kiểm tra công thức giải được cube trước khi mở UART.

Đặt Rubik theo đúng hướng U/R/F/D/L/B của chuỗi trạng thái và đưa cơ cấu về
trạng thái sẵn sàng. Script không tự RESET. CLI cũ
`python -m rubik_robot.main --mode send --cube "..."` (chạy từ rpi) giữ bước
khởi tạo cơ cấu bằng RUBIK RESET trước khi gửi lời giải.

## Quy đổi công thức

`R U' F2` tương ứng:

```text
RUBIK MOVE R
RUBIK MOVE U_
RUBIK MOVE F
RUBIK MOVE F
```

UARTSession tự thêm ID và newline lúc gửi. File xuất chỉ chứa nội dung lệnh,
không phải các frame có ID cố định để ghi thẳng vào serial.
Planner nhận cả ký hiệu chuẩn, hậu tố `_`, và ký hiệu Two-Phase `R1/U3/F2`.

Mỗi action vẫn là một nước logic. `F2` hoàn thành sau hai DONE. Nếu nửa sau
lỗi, exception có `completed_quarter_turns=1`; không tính cả F2 đã hoàn thành.
Không tự gửi lại. Hủy chuỗi có hiệu lực sau nước đang chạy, gồm cả hai nửa F2.

Các lựa chọn Python cũ TURN/MOVE được giữ cho nơi gọi cũ, nhưng đều xuất
RUBIK MOVE. `duration_ms` chỉ là ước lượng; handler C hiện không sử dụng nó
để điều chỉnh servo, nên Python không ghép thời gian vào lệnh gửi.

## Tầng UART và giới hạn firmware

UARTSession nhận port/baudrate riêng, timeout OK mặc định 1 giây và timeout
DONE 30 giây mỗi lệnh. Session lỗi ngừng nhận lệnh tiếp; kiểm tra trạng thái
Rubik rồi đóng/tạo lại phiên. ID dùng 1..65535, không quay vòng trong một phiên.
Hàm gọi trực tiếp `move_Front()` vẫn trả bool; solver truyền session để nhận
thông tin lỗi và tiến độ chi tiết.

Auto Solve dùng `RUBIK SCAN_BEGIN` và `RUBIK SCAN_POSE <face>` để chuẩn bị
và đổi tư thế toàn khối. Xem [cách chạy Auto Solve](AUTO_SOLVE.md).
Các hàm ghép LR/UD vẫn bị từ chối vì handler firmware chưa hỗ trợ.
RUBIK STOP chưa được triển khai trong C; nút Stop hủy các lệnh tiếp theo.

Kiểm thử không dùng phần cứng, chạy từ rpi:

```sh
python -m pytest tests/test_uart_solver.py tests/test_motion_planner.py tests/test_scramble.py tests/test_auto_solve.py
```

Các bài kiểm thử Workspace cần Tk/Tcl. Có thể kiểm tra logic bằng cách thêm
`-k "not Workspace"` nếu môi trường không có giao diện.
