# Rubik RPi STM32 Solver

Hệ thống Rubik 3×3 gồm web camera, bộ giải Two-Phase, bộ tạo đề, xuất lệnh UART và thư viện điều khiển servo STM32.

## Chức năng và điểm chạy

| Thành phần     | Chức năng                                                          | Điểm chạy                                 |
| -------------- | ------------------------------------------------------------------ | ----------------------------------------- |
| Rubik Studio   | Hướng dẫn camera, tạo đề, quét sáu mặt và xuất UART                | `scripts/run_web.py`, cổng 5000           |
| Web 3D         | Mô hình cube, xoay thử, trộn, mô phỏng lời giải, pause/resume/step | `rpi/twophase/start_server.py`, cổng 8080 |
| GUI desktop    | Nhập màu bằng chuột/webcam, chỉnh ngưỡng, xem lời giải             | `scripts/run_vision_gui.py`               |
| CLI            | Giải cube string và in lệnh TURN/MOVE                              | `rubik_robot.main --mode solve`           |
| UART           | Mở cổng serial, gửi lệnh và đọc phản hồi                           | Cần board/firmware phù hợp                |
| Firmware servo | Profile PWM, calibration góc, HOME/STOP/kẹp                        | Tích hợp bằng STM32CubeIDE                |

Web mới xuất lệnh để bàn giao cho bộ UART; không thực hiện giao tiếp PCA9685. Việc lật cả khối và phối hợp servo để xoay mặt cần bộ điều khiển cơ khí tương ứng.

## 1. Chuẩn bị trên Windows

Mở PowerShell tại thư mục gốc project. Python phải từ 3.10 trở lên:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r rpi\requirements.txt
.\.venv\Scripts\python.exe -B -c "import cv2, numpy, serial, tkinter; print('Thu vien OK')"
```

Dùng trực tiếp Python trong `.venv`; không cần đổi ExecutionPolicy hoặc kích hoạt môi trường. Các lệnh bên dưới đều bắt đầu từ thư mục gốc, trừ khối có `Push-Location`.

## 2. Chạy web ba chức năng

Đóng ứng dụng đang dùng Logitech, rồi chạy:

```powershell
.\.venv\Scripts\python.exe -B scripts\run_web.py --camera 1 --backend dshow --port 5000
```

Mở **http://127.0.0.1:5000**. Không cần Node.js, build frontend hoặc server solver riêng. Camera chỉ mở khi bấm nút trên web. Nếu Logitech có ID khác, chọn lại trong phần thiết lập.

### Hướng dẫn giải bằng camera

1. Chọn **Hướng dẫn giải → Mở camera**.
2. Bấm **Bắt đầu quét & hướng dẫn**; đưa lần lượt F → U → D → R → L → B theo lời nhắc.
3. Chương trình tự ghi mỗi mặt sau bỏ phiếu 5 mẫu hợp lệ; không cần bấm ghi từng mặt hoặc hiệu chỉnh LAB.
4. Sau khi giải trạng thái, đưa mặt trước về camera và làm theo mũi tên trực tiếp trên video.
5. Mỗi thao tác được xác nhận bằng 10 mẫu mặt. Nước 180° thực hiện hai lần 90°; mặt B có bước đổi hướng cả khối và đưa trở lại.

Toàn bộ chức năng 1 nằm trong hai file `rpi/rubik_robot/web/camera_tutorial.py` và `tutorial_moves.py`: quét/tìm lời giải/điều phối và các hàm xoay/vẽ mũi tên/xác nhận. Web chỉ gọi bắt đầu/dừng, đọc trạng thái và hiển thị ảnh đã xử lý. Chức năng 3 vẫn dùng khung bốn góc và calibration LAB riêng.

### Tạo bộ đề

Chọn **Tạo bộ đề**, chọn Dễ/Trung bình/Khó và tạo đề. Các mức dùng lần lượt 5/12/22 nước trộn. Tải riêng lệnh **TRỘN**, lệnh **GIẢI** hoặc JSON cả bộ đề. Độ dài chuỗi trộn không phải độ sâu tối ưu của trạng thái.

### Quét tự động và xuất lời giải

Chọn **Giải tự động**. Thứ tự chụp cố định: **U → F → D → B → R → L**. Sau khi chụp đủ, khối phải trở về tư thế ban đầu rồi mới xuất lời giải.

- **Mô phỏng:** chạy đủ quy trình, không dùng camera/UART.
- **Tự đổi tư thế:** dùng camera thật; người vận hành lật cả khối rồi xác nhận DONE.
- **Bộ UART ngoài:** bộ giao tiếp thực hiện lệnh REORIENT, trả DONE đúng ID qua API; web tự chụp khi hình ổn định.

Chi tiết tư thế, calibration, API và lệnh test nằm trong [hướng dẫn chạy đầy đủ](docs/WEB_STUDIO.md).

## 3. Web 3D và GUI desktop

Chạy server dùng chung cho web 3D và GUI:

```powershell
.\.venv\Scripts\python.exe -B rpi\twophase\start_server.py
```

Mở **http://127.0.0.1:8080** để xem mô hình 3D. Thử trạng thái/ngẫu nhiên, xoay một nước và chạy lời giải ở chế độ **simulated**. Giao diện có pause/resume/step/stop và trạng thái các actuator mô phỏng.

Nếu cần GUI desktop, giữ server chạy và mở terminal khác:

```powershell
.\.venv\Scripts\python.exe -B scripts\run_vision_gui.py
```

GUI kết nối `localhost:8080`. Mặc định GUI desktop dùng camera 0 và bộ màu tâm khác web mới; xem bảng hướng dẫn trong docs. Không mở GUI desktop và web camera cùng lúc trên cùng Logitech.

## 4. CLI giải và xuất lệnh

```powershell
.\.venv\Scripts\python.exe -B scripts\demo_pipeline.py

Push-Location rpi
..\.venv\Scripts\python.exe -B -m rubik_robot.main --mode solve --cube "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL" --face-turn-command TURN
Pop-Location
```

Demo dùng cube hoàn chỉnh nên in `already solved` và danh sách hành động rỗng. CLI với cube mẫu in lời giải và lệnh TURN; không điều khiển servo. Đổi sang `--face-turn-command MOVE` nếu cần định dạng cũ.

## 5. UART và STM32

Liệt kê cổng COM:

```powershell
.\.venv\Scripts\python.exe -B -m serial.tools.list_ports
```

Với board đã có firmware phù hợp, thay COM5 bằng cổng thực tế:

```powershell
.\.venv\Scripts\python.exe -B -m serial.tools.miniterm COM5 115200 --eol LF --echo
```

Gửi `PING`, chờ `OK PONG`; thoát bằng `Ctrl+]`. Chỉ chạy chuyển động khi profile PWM và cơ khí đã được cấu hình. Firmware hiện có chưa triển khai sequence TURN/MOVE/SCAN_POSE và chưa hỗ trợ REORIENT.

Tài liệu nội bộ: [UART](docs/UART_PROTOCOL.md), [CubeIDE](docs/CUBEIDE_SETUP.md), [driver servo](firmware/stm32cubeide/App/SERVO_CONTROLLER_GUIDE.md).

## 6. Chạy kiểm thử

```powershell
Push-Location rpi
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
Pop-Location

.\.venv\Scripts\python.exe -B firmware\tests\run_tests.py
```

Test firmware cần GCC trong PATH hoặc biến `CC`. Test dùng HAL giả, không chạy motor. Test camera dùng ảnh tổng hợp; cần kiểm chứng màu, ánh sáng và cơ khí trên thiết bị thật.

## Raspberry Pi

Tại thư mục gốc:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r rpi/requirements.txt
.venv/bin/python -B scripts/run_web.py --camera 0 --backend v4l2 --port 5000
```

Chọn camera/backend theo thiết bị thực tế. Dùng `Ctrl+C` để dừng server.

## Cấu trúc chính

```text
rpi/rubik_robot/web/       Camera, nhận màu, hướng dẫn, bộ đề, kế hoạch quét và HTTP
rpi/rubik_robot/cube/      Cube string và phép xoay
rpi/rubik_robot/motion/    Tạo lệnh TURN/MOVE
rpi/rubik_robot/transport/ Giao tiếp serial
rpi/twophase/              Bộ giải Two-Phase và bảng tính trước
rpi/tests/                 Kiểm thử Python/API
scripts/                   Các điểm chạy ứng dụng
firmware/                  Thư viện STM32, snippet và test HAL giả
calibration/               Profile màu/phần cứng theo máy
docs/                      Hướng dẫn chạy, kiến trúc và giao thức
```
