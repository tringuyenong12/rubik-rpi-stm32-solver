# Ghi chú thực thi và chạy trên Raspberry Pi

Tài liệu mô tả mã hiện tại của dự án, cập nhật ngày 18/11/2026.
Môi trường hướng dẫn: **Raspberry Pi 4, Raspberry Pi OS 64-bit, Python 3.10 trở lên**, camera USB và STM32F411 dùng USART1.

Đường dẫn ví dụ trên Pi là `~/rubik-rpi-stm32-solver`. Thay đường dẫn này nếu bạn chép dự án vào nơi khác.
Các lệnh dưới đây chạy trên terminal Linux của Pi. Phần cài đặt, bật UART chỉ cần làm khi thiết lập máy.

## 1. Chương trình hiện làm được gì?

| Chức năng | Cách chạy | Trạng thái |
|---|---|---|
| Tìm lời giải từ chuỗi 54 ô | `scripts/run_solver.py --cube ...` | Có |
| Kiểm tra và gửi lời giải xuống STM32 | Thêm `--port /dev/serial0` | Có, dùng UART mới |
| Đọc trạng thái/công thức đã lưu | `scripts/run_solver.py --input ...json` | Có |
| Tạo và gửi công thức trộn Rubik | `scripts/run_scramble.py` | Có |
| Camera nhận màu, người dùng đổi mặt bằng tay, hiển thị lời giải | `scripts/run_vision_gui.py` | Có; cần Desktop và camera |
| Robot tự đổi tư thế để chụp đủ sáu mặt rồi giải | Chế độ `Auto Solve` | Đang chặn: firmware chưa có `SCAN_POSE` |
| Calibration servo | `rpi/Rubik_Cube/Calibration/` | Giữ nguyên; không thuộc hướng dẫn chuyển solver này |

**Auto scan của camera không đồng nghĩa với robot tự xoay khối để quét.** Camera có thể tự lưu một mặt khi ảnh ổn định, nhưng bạn vẫn phải đưa từng mặt vào camera ở luồng quét thủ công.

Một số phần trong `README.md` và tài liệu cũ còn mô tả `TURN R 1 450`, `MOVE R -1 450`, `HOME`. Luồng solver hiện dùng `RUBIK MOVE`, ID giao dịch và phản hồi `>#ID` như bên dưới.

## 2. Các thư mục và trách nhiệm

```text
rubik-rpi-stm32-solver/
├── scripts/
│   ├── run_solver.py          Điểm chạy lời giải từ cube/JSON
│   ├── run_scramble.py        Tạo công thức trộn, tùy chọn gửi
│   ├── run_vision_gui.py      Mở camera và giao diện
│   ├── demo_pipeline.py       Demo solver/planner, không gửi UART
│   └── evaluate_vision.py     Đánh giá nhận diện, không gửi lệnh xoay
├── rpi/
│   ├── Rubik_Cube/
│   │   ├── motion/motion.py   Các hàm move_Front(), move_Right_()...
│   │   ├── UART_Command/
│   │   │   ├── UART_Command.py  API gửi lệnh, hàm bool, phiên mặc định
│   │   │   ├── session.py       Mở cổng, ID, timeout, nhận OK/DONE/ERR
│   │   │   └── test_UART_Command.py  Terminal nhập lệnh tương tác
│   │   └── Calibration/      Công cụ calibration riêng
│   ├── rubik_robot/
│   │   ├── cube/state.py     Quy ước và kiểm tra chuỗi trạng thái
│   │   ├── solver/
│   │   │   ├── kociemba_solver.py  Gọi solver, chuẩn hóa công thức
│   │   │   └── execution.py       Kiểm tra cube và tính đúng của lời giải
│   │   ├── motion/planner.py Chuyển công thức thành action logic
│   │   ├── protocol.py       MoveCommand và nội dung lệnh STM32
│   │   ├── transport/
│   │   │   ├── scramble_sender.py  Gửi tuần tự, tiến độ, hủy, lỗi
│   │   │   └── serial_link.py      Gọi các hàm motion qua UARTSession
│   │   ├── vision/           Camera, nhận màu, kiểm tra ảnh/trạng thái
│   │   ├── main.py           CLI theo --mode demo/solve/send
│   │   └── auto_solve.py     Luồng quét bằng robot, hiện chưa tương thích
│   ├── twophase/             Thuật toán Two-Phase và server TCP tùy chọn
│   └── tests/                Kiểm thử Python
├── firmware/rubik_stm32_ver1/ Firmware hiện đối chiếu với Python
├── calibration/              Dữ liệu camera và bản ghi lần quét
└── docs/solver_uart.md        Ghi chú ngắn về chuyển đổi UART
```

`rubik_robot/motion/planner.py` và `Rubik_Cube/motion/motion.py` có vai trò khác nhau:

- **Planner:** tính danh sách cần làm; gọi planner không làm servo chuyển động.
- **Motion:** thực hiện một lệnh xoay bằng cách gọi tầng UART.
- **SerialLink hiện tại:** là lớp kết nối các action cũ với tầng mới; không còn tự ghép frame và tự đọc serial như trước.

Tên `scramble_sender.py` vẫn được giữ, nhưng hàm `send_actions()` bên trong được dùng chung cho cả trộn và giải.

## 3. Khi gọi run_solver.py, những hàm nào chạy?

Ví dụ:

```bash
.venv-pi/bin/python -B scripts/run_solver.py --input solution.json --port /dev/serial0
```

```text
run_solver.main()
  │ đọc --cube hoặc JSON; đọc --solution nếu có
  ▼
solver.execution.solution_plan()
  ├─ validate_cube_string(): kiểm tra 54 ô, ký tự, số lượng
  ├─ FaceCube / CubieCube.verify(): kiểm tra cấu hình Rubik hợp lệ
  ├─ solve_cube(): tìm lời giải nếu người dùng chưa cung cấp
  │    └─ twophase.solver.solve() → chuẩn hóa U1/U3 thành U/U'
  ├─ MotionPlanner.plan(): công thức → list[PlannedAction]
  └─ Áp dụng công thức lên mô hình cube để kiểm tra kết quả đã giải
  │
  ├─ Không có --port: in/xuất kế hoạch rồi kết thúc
  │
  ▼ có --port
transport.scramble_sender.send_actions()
  ├─ Mở SerialLink → UARTSession.open()
  ├─ Gửi RUBIK PING và chờ DONE
  └─ Với từng action:
       SerialLink.request_completed(action.command)
         └─ motion.move_R(), move_U_(), move_F()...
              └─ motion.move(token, session=...)
                   └─ Send_Command_to_STM32(body, session=...)
                        └─ UARTSession.request(body)
                             ├─ Thêm #ID và newline
                             ├─ serial.write() / flush()
                             └─ Chờ >#ID OK rồi >#ID DONE
  │
  └─ Báo tiến độ; đóng UART khi xong hoặc khi lỗi
```

Các điểm cần nhớ:

1. `scripts/run_solver.py` tự thêm thư mục `rpi` vào đường tìm module. Khi dùng script này, không cần tự đặt `PYTHONPATH`.
2. `solution_plan()` chưa mở UART; công thức sai bị từ chối trước khi gửi.
3. Solver CLI này chạy thuật toán tại chỗ, **không cần khởi động server TCP**.
4. Nếu cube đã giải và không có action, `send_actions()` không mở cổng hay gửi PING.
5. Script không tự RESET cơ cấu. Cơ cấu cần được chuẩn bị sẵn trước khi gửi.
6. Gọi `send_solution()` trong `solver/execution.py` cũng thực hiện kiểm tra lời giải rồi gọi `send_actions()`.

### 3.1. Trạng thái cube và hướng đặt khối

Chuỗi cube có 54 ký tự theo thứ tự:

```text
U1..U9 R1..R9 F1..F9 D1..D9 L1..L9 B1..B9
```

Mỗi nhóm chín ô là một mặt, đọc theo hàng từ trái sang phải, trên xuống dưới theo quy ước mặt của solver. Ký tự U/R/F/D/L/B biểu thị màu thuộc mặt tâm tương ứng, không phải tên màu viết bằng tiếng Việt.

Trạng thái đã giải:

```text
UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
```

Khối thật phải được đặt đúng hệ hướng dùng trong chuỗi. Với cấu hình màu mặc định của giao diện: U vàng, R xanh lá, F đỏ, D trắng, L xanh biển, B cam. Đặt F về phía cơ cấu Front, U lên trên, R về bên Right của máy. Đặt khác hướng có thể khiến công thức đúng trên mô hình nhưng xoay sai trên máy.

### 3.2. Công thức → hàm → lệnh UART

| Nước solver | Hàm motion được gọi | Nội dung lệnh |
|---|---|---|
| `R` hoặc `R1` | `move_R()` → alias của `move_Right()` | `RUBIK MOVE R` |
| `U'`, `U_` hoặc `U3` | `move_U_()` → alias của `move_Up_()` | `RUBIK MOVE U_` |
| `F2` | `move_F()` hai lần | Hai lệnh `RUBIK MOVE F` |

Ví dụ `R U' F2` là **ba nước logic nhưng bốn lệnh xoay vật lý**. Mỗi action của planner vẫn ứng với một nước logic, nên F2 không làm lệch tiến độ lời giải.

Với một phiên mới và chuỗi trên, log dự kiến:

```text
[TX] #1 RUBIK PING
[RX] >#1 OK
[RX] >#1 DONE
[TX] #2 RUBIK MOVE R
[RX] >#2 OK
[RX] >#2 DONE
[TX] #3 RUBIK MOVE U_
[RX] >#3 OK
[RX] >#3 DONE
[TX] #4 RUBIK MOVE F
[RX] >#4 OK
[RX] >#4 DONE
[TX] #5 RUBIK MOVE F
[RX] >#5 OK
[RX] >#5 DONE
```

Đây là ví dụ giao thức; công thức `R U' F2` chỉ được `run_solver.py` gửi nếu nó thực sự giải được cube đầu vào.

## 4. STM32 tiếp nhận lệnh thế nào?

```text
USART1 nhận byte
  → UART_Command_RxCallback(): ghép frame từ # đến newline
  → main loop gọi UART_Command_Process()
  → parser tách ID / nhóm / hành động / mặt
  → Rubik_CommandHandler()
  → UART_Accept(id): trả >#ID OK
  → Rubik_Front(), Rubik_Right_(), ... điều khiển servo
  → UART_Done(id): trả >#ID DONE
```

Firmware hiện tại gọi `UART_Command_Init(&huart1)` khi khởi động và `UART_Command_Process()` trong vòng lặp chính. Chuỗi chào khởi động STM32 không phải phản hồi hoàn thành một lệnh.

| Thuộc tính | Giá trị hiện tại |
|---|---|
| UART STM32 | USART1, TX PA9, RX PA10 |
| Serial | 115200 baud, 8 data bits, no parity, 1 stop bit |
| Frame gửi | `#<ID> RUBIK MOVE <mặt>\n` |
| Phản hồi | `>#<ID> OK`, `>#<ID> DONE`, `>#<ID> ERR <lỗi>` |
| ID Python | 1..65535 trong một phiên, không tự quay vòng |
| Mặt nhận trong handler | U/D/L/R/F/B và sáu dạng có hậu tố `_` |

README firmware có ví dụ thêm `duration_ms`, nhưng handler C hiện chưa dùng tham số đó để điều chỉnh servo. Python hiện gửi mặt thôi. Các tùy chọn cũ `TURN`/`MOVE` đều được chuyển thành `RUBIK MOVE`; `duration_ms` trong planner chỉ dùng để ước lượng.

## 5. Chuẩn bị Python trên Raspberry Pi

Chép cả dự án sang Pi, bao gồm `rpi`, `scripts`, `docs` và các dữ liệu cấu hình cần dùng. Tạo môi trường Python riêng trên Pi; không chép `.venv` Windows sang Linux.

```bash
cd ~/rubik-rpi-stm32-solver
python3 --version

sudo apt update
sudo apt install -y python3-venv python3-opencv python3-numpy python3-serial python3-tk python3-pytest v4l-utils

python3 -m venv --system-site-packages .venv-pi
.venv-pi/bin/python -c 'import cv2, numpy, serial, tkinter; print("Thu vien OK")'
.venv-pi/bin/python -B scripts/run_solver.py --help
```

`--system-site-packages` cho môi trường ảo dùng các thư viện đã cài bằng APT. Cách gọi `.venv-pi/bin/python` không yêu cầu activate môi trường.

Solver Two-Phase đã nằm trong `rpi/twophase`. Lần chạy solver trên cube chưa giải có thể tạo các bảng tra và mất nhiều thời gian hơn các lần sau; cần đợi thông báo hoàn thành. Nếu đã cung cấp công thức hợp lệ qua `--solution` hoặc JSON, chương trình chỉ kiểm tra công thức đó, không cần tìm lại.

## 6. Đấu dây và bật UART trên Pi 4

| Raspberry Pi 4 | STM32 theo cấu hình hiện tại |
|---|---|
| GPIO14 TX, chân vật lý 8 | PA10 RX |
| GPIO15 RX, chân vật lý 10 | PA9 TX |
| GND | GND |

UART GPIO dùng mức 3,3 V, không nối tín hiệu 5 V. TX nối RX và RX nối TX. Pi 5 có ánh xạ UART mặc định khác; bảng này dành cho Pi 4. [Nguồn cấu hình UART Raspberry Pi](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-uarts).

```bash
sudo raspi-config
```

Chọn **Interface Options → Serial Port**: tắt login shell qua serial (**No**), bật UART hardware (**Yes**), rồi reboot. [Hướng dẫn chính thức](https://www.raspberrypi.com/documentation/computers/configuration.html#disable-the-linux-serial-console).

```bash
sudo reboot
```

Sau khi đăng nhập lại:

```bash
cd ~/rubik-rpi-stm32-solver
ls -l /dev/serial0
readlink -f /dev/serial0
groups
```

Nếu tài khoản chưa có quyền dùng thiết bị thuộc nhóm `dialout`:

```bash
sudo usermod -aG dialout "$USER"
```

Đăng xuất/đăng nhập lại để nhóm có hiệu lực. Dùng Python bằng tài khoản thường, không cần chạy toàn bộ chương trình bằng sudo.

Nếu dùng USB-UART thay cho GPIO, liệt kê cổng và truyền đúng tên thiết bị:

```bash
.venv-pi/bin/python -m serial.tools.list_ports
```

Ví dụ có thể là `/dev/ttyUSB0`; tên thực tế lấy từ kết quả liệt kê. Cổng đang được terminal UART sử dụng cần đóng trước khi chạy solver.

## 7. Kiểm tra PING trước khi gửi chuyển động

Từ thư mục gốc dự án:

```bash
.venv-pi/bin/python -B rpi/Rubik_Cube/UART_Command/test_UART_Command.py
```

Tại dấu nhắc `UART>`, nhập:

```text
RUBIK PING
```

Không thêm `#ID`, không gõ ký tự `\n` vào cuối; module tự thêm chúng. Kết quả mong đợi là `>#1 OK` rồi `>#1 DONE` trong phiên mới. Nhập `exit` để đóng terminal và giải phóng cổng.

Terminal này mặc định dùng `/dev/serial0`. Nếu cần kiểm tra cổng khác, dùng đoạn Python sau từ thư mục gốc:

```bash
.venv-pi/bin/python - <<'PY'
import sys
sys.path.insert(0, 'rpi')
from Rubik_Cube.UART_Command.session import UARTSession

uart = UARTSession('/dev/ttyUSB0', baudrate=115200)
try:
    print(uart.request('RUBIK PING'))
finally:
    uart.close()
PY
```

`RUBIK RESET` đưa cơ cấu về trạng thái khởi đầu theo hàm firmware, **không giải Rubik về sáu mặt đồng màu**. Chỉ gọi RESET khi bạn chủ động muốn thực hiện bước khởi tạo cơ cấu.

## 8. Chạy solver từ chuỗi trạng thái hoặc JSON

### 8.1. Kiểm tra không chuyển động

Ví dụ cube đã giải để kiểm tra cài đặt:

```bash
cd ~/rubik-rpi-stm32-solver
.venv-pi/bin/python -B scripts/run_solver.py \
  --cube UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB
```

Kết quả có `<already solved>`, không mở UART. Với cube chưa giải, thay bằng chuỗi 54 ô thực tế; không có `--port` thì chỉ tính và hiển thị kế hoạch.

### 8.2. JSON mẫu có trạng thái và lời giải đã biết

Ví dụ này tương ứng với trạng thái sau chuỗi trộn `R2 U' R' B' L` từ cube đã giải; công thức ngược là `L' B R U R2`.

```bash
cat > example_solution.json <<'JSON'
{
  "cube": "ULFBUFBURBRDFRDFRFLLDUFUUFULDLFDBFRRBDDLLBLLBRBRRBDUUD",
  "solution": "L' B R U R2"
}
JSON

.venv-pi/bin/python -B scripts/run_solver.py --input example_solution.json
```

JSON mẫu chỉ dùng để kiểm tra phần mềm. Chỉ gửi chuyển động khi cube thật đúng trạng thái và hướng của JSON.

Trường `cube` bắt buộc, `solution` tùy chọn. Nếu bỏ `solution`, chương trình tự tìm lời giải. Nếu truyền thêm `--solution`, công thức trên dòng lệnh được ưu tiên hơn trường trong JSON.

### 8.3. Xuất lệnh và gửi dữ liệu thật

Sau khi chuẩn bị `solution.json` cho cube thật:

```bash
# Xem trước và xuất nội dung lệnh, không gửi:
.venv-pi/bin/python -B scripts/run_solver.py \
  --input solution.json --output commands.txt

# Gửi khi cơ cấu và cube đã sẵn sàng:
.venv-pi/bin/python -u -B scripts/run_solver.py \
  --input solution.json --port /dev/serial0 --baudrate 115200 --timeout 30
```

`commands.txt` chứa nội dung như `RUBIK MOVE F`, chưa có ID. Không ghi trực tiếp file này vào cổng serial; hãy để script và UARTSession gửi, ghép ID và chờ phản hồi.

| Tùy chọn run_solver.py | Ý nghĩa |
|---|---|
| `--cube` | Chuỗi trạng thái 54 ô |
| `--input` | JSON đầu vào; chọn một trong `--cube` và `--input` |
| `--solution` | Công thức đã biết; vẫn được kiểm tra tính đúng |
| `--output` | Xuất nội dung lệnh |
| `--port` | Có tham số này mới gửi UART |
| `--baudrate` | Mặc định 115200 |
| `--timeout` | Thời gian chờ DONE cho mỗi lệnh vật lý, mặc định 30 giây |

## 9. Chạy camera và chuyển kết quả sang solver UART

GUI cần phiên Desktop trên Pi hoặc phiên VNC có màn hình. Các lệnh solver/serial không dùng GUI có thể chạy qua SSH.

```bash
cd ~/rubik-rpi-stm32-solver
v4l2-ctl --list-devices
.venv-pi/bin/python -B scripts/run_vision_gui.py --camera 0 --backend v4l2
```

Nếu camera đúng nằm ở chỉ số khác, thay `--camera 0`. Hướng dẫn này dành cho camera USB mà OpenCV mở được; camera CSI cần cấu hình đường lấy ảnh phù hợp riêng.

Luồng GUI:

```text
run_vision_gui.py
  → twophase.vision2: lấy ảnh camera trong luồng nền
  → twophase.client_gui2: Tkinter, quản lý sáu mặt
  → vision/solve_guide.py: kiểm tra trạng thái và yêu cầu lời giải
  → server TCP hoặc solver tại chỗ khi fallback localhost phù hợp
  → solution_panel.py: hiển thị công thức và hình hướng dẫn
```

Thao tác thông thường:

1. Chọn vùng nhận diện và đưa trọn chín ô của một mặt vào camera.
2. Giữ yên để camera lưu, rồi tự đổi sang mặt tiếp theo.
3. Thu đủ sáu mặt và yêu cầu Solve; sửa/quét lại nếu trạng thái bị từ chối.
4. Ghi nhận chuỗi cube và công thức trong giao diện.
5. Đặt cube vào máy đúng hướng, không làm thay đổi trạng thái các lớp trong quá trình chuyển.
6. Dùng `run_solver.py` gửi lời giải đã kiểm tra.

**Solve Guide hiển thị công thức, không tự gửi các nước đó đến STM32.** Chế độ Scramble trong GUI có luồng gửi riêng. Chế độ robot Auto Solve hiện báo chưa hỗ trợ SCAN_POSE.

### 9.1. Lấy cube từ bản ghi quét

GUI ghi đầu vào solver tại `calibration/last_solver_input.json`. File này dùng khóa `solver_cube`, không phải `cube`, và có thể thuộc một lượt quét cũ. Chỉ chuyển dữ liệu sau khi xác nhận đó là lượt quét hiện tại đã được chấp nhận.

Đoạn sau đọc bản ghi, tạo file mới ở thư mục gốc; không thay đổi calibration:

```bash
.venv-pi/bin/python - <<'PY'
import json
from pathlib import Path

audit = json.loads(Path('calibration/last_solver_input.json').read_text(encoding='utf-8'))
if audit.get('status') != 'validated' or 'solver_cube' not in audit:
    raise SystemExit('Lan quet chua hop le; hay kiem tra giao dien va quet lai.')
payload = {'cube': audit['solver_cube']}
Path('solution.json').write_text(json.dumps(payload, indent=2), encoding='utf-8')
print('Da tao solution.json; hay doi chieu cube voi lan quet hien tai.')
PY

.venv-pi/bin/python -B scripts/run_solver.py --input solution.json
```

File mới chỉ có cube nên CLI sẽ tìm lời giải lại. Bạn có thể thêm trường `solution` lấy từ giao diện; CLI vẫn kiểm tra công thức đó trước khi gửi.

### 9.2. Server solver tùy chọn

Nếu muốn chạy server cho GUI, mở terminal riêng:

```bash
cd ~/rubik-rpi-stm32-solver
.venv-pi/bin/python -u -B rpi/twophase/start_server.py 8080 20 3
```

Các tham số là cổng TCP, số nước tối đa, thời gian tìm kiếm yêu cầu. Đợi server sẵn sàng, rồi mở GUI ở terminal khác. TCP 8080 là giao tiếp GUI–solver, không phải UART 115200 baud.

GUI hỗ trợ fallback solver tại chỗ khi kết nối localhost bị từ chối theo logic `request_solution()`. CLI `run_solver.py` không dùng server này.

## 10. Tạo và gửi scramble

```bash
cd ~/rubik-rpi-stm32-solver

# Sinh đề, in công thức và target cube, chưa gửi:
.venv-pi/bin/python -B scripts/run_scramble.py --level easy --seed 1

# Xuất nội dung lệnh:
.venv-pi/bin/python -B scripts/run_scramble.py \
  --level easy --seed 1 --output scramble_commands.txt

# Thực hiện trên cube thật đang ở trạng thái đã giải:
.venv-pi/bin/python -u -B scripts/run_scramble.py \
  --level easy --seed 1 --port /dev/serial0 --timeout 30
```

`easy`, `medium`, `hard` tương ứng 5, 12, 22 nước logic. `--seed` giúp tạo lại cùng một chuỗi. Cube thật phải bắt đầu ở trạng thái đã giải thì `Target cube` được in mới phản ánh trạng thái sau khi chạy thành công.

```text
run_scramble.py → create_scramble() → MotionPlanner.plan()
               → send_scramble() → send_actions()
               → SerialLink → motion → UART_Command → UARTSession
```

Script trộn cũng gửi PING trước, không tự RESET cơ cấu.

## 11. CLI cũ và gọi từ Python

### 11.1. CLI rubik_robot.main

Lệnh dùng `-m rubik_robot.main` cần chạy từ `rpi/` để tìm thấy package:

```bash
cd ~/rubik-rpi-stm32-solver/rpi
../.venv-pi/bin/python -B -m rubik_robot.main --mode demo
```

| Chế độ | Hành vi |
|---|---|
| `demo` hoặc `solve` | Kiểm tra cube, tìm/kiểm tra lời giải, in kế hoạch |
| `send` | Có nước cần xoay: mở UART → PING → RESET → các nước giải |

Khác biệt cần nhớ: `main.py --mode send` có bước `RUBIK RESET`, còn `run_solver.py --port ...` không có. Khi cube đã giải, cả hai không cần gửi nước xoay; main cũng không RESET trong trường hợp này.

### 11.2. Gọi từng mặt trực tiếp

Ví dụ chạy từ `rpi/`, dùng cổng mặc định `/dev/serial0`:

```python
from Rubik_Cube.motion.motion import move_Front, move_Front_, U, R_
from Rubik_Cube.UART_Command.UART_Command import UART_Close

try:
    for action in (move_Front, move_Front_, U, R_):
        if not action():
            break
finally:
    UART_Close()
```

Đây là đoạn thực hiện chuyển động, không phải bản xem trước. Mỗi hàm trả bool, gọi blocking đến khi hoàn thành hoặc lỗi. Import module không mở UART; lần gọi gửi đầu tiên mới mở cổng.

### 11.3. Gọi lời giải từ chương trình khác

```python
from rubik_robot.solver.execution import send_solution

# cube là chuỗi 54 ô lấy từ trạng thái thật đã kiểm tra.
result = send_solution(
    cube,
    port='/dev/serial0',
    baudrate=115200,
    timeout_s=30,
    progress=lambda count, reply: print(count, reply),
)
print(result.completed, result.cancelled)
```

Có thể truyền `solution="..."` để dùng công thức đã biết, hoặc `cancel` là `threading.Event` để hủy các nước tiếp theo. Nếu dùng trong GUI, chạy gửi ở worker thread vì các hàm này chờ UART theo kiểu blocking.

## 12. Timeout, dừng và trạng thái sau lỗi

- Timeout OK mặc định 1 giây; khi `--timeout` nhỏ hơn 1 giây, giới hạn chờ OK cũng bị thu ngắn theo.
- Sau khi nhận OK, bắt đầu thời gian chờ DONE của lệnh đó; mặc định 30 giây. Đây không phải giới hạn tổng thời gian giải.
- Chỉ DONE đúng ID sau OK mới xác nhận một lệnh hoàn thành. Log debug và phản hồi ID khác bị bỏ qua.
- Nếu F2 lỗi ở lần F thứ hai, nước F2 chưa được tính hoàn thành; lỗi báo một quarter-turn đã xác nhận.
- ERR, mất phản hồi hoặc lỗi serial làm chuỗi dừng; không tự retry vì có thể tạo thêm một lần xoay.
- Hủy bằng Event/nút Stop chặn các nước tiếp theo sau nước logic đang chạy, bao gồm cả hai nửa F2.
- Ctrl+C có thể ngắt chương trình khi lệnh vẫn đang chạy trên STM32; đây không phải xác nhận servo đã dừng.
- `UART_Command_Stop()` trên STM32 hiện còn rỗng. Chưa có chức năng dừng cơ cấu tức thời qua giao thức này.
- Sau lỗi chuyển động, kiểm tra hoặc quét lại trạng thái cube trước khi dùng một lời giải mới; không gửi lại toàn bộ công thức cũ từ đầu.

## 13. Kiểm thử và xử lý lỗi thường gặp

Kiểm thử phần mềm bằng UART giả lập, không cần cắm STM32:

```bash
cd ~/rubik-rpi-stm32-solver/rpi
../.venv-pi/bin/python -B -m pytest \
  tests/test_uart_solver.py tests/test_motion_planner.py \
  tests/test_scramble.py tests/test_auto_solve.py \
  -q -k "not Workspace"
```

Bỏ `-k "not Workspace"` khi muốn chạy cả kiểm thử giao diện và môi trường đã có Tk/Tcl hoạt động. Kết quả kiểm thử giả lập không xác nhận dây điện, chiều servo hay cơ cấu thực tế.

| Hiện tượng | Kiểm tra / cách xử lý |
|---|---|
| `No module named rubik_robot` | Chạy script từ gốc repo, hoặc chạy `-m rubik_robot.main` từ `rpi/` |
| Thiếu `cv2`, `serial`, `numpy` | Dùng đúng `.venv-pi/bin/python`, kiểm tra các gói APT và `--system-site-packages` |
| Không có `/dev/serial0` | Kiểm tra cấu hình UART, reboot và loại Pi đang dùng |
| `Permission denied` khi mở UART | Kiểm tra quyền thiết bị và nhóm dialout, đăng nhập lại sau khi thêm nhóm |
| Chờ `#ID OK` hết hạn | Kiểm tra cổng, baudrate, TX/RX/GND, firmware đang chạy vòng xử lý UART và có trả đúng `>#ID` |
| Có OK nhưng không DONE | Kiểm tra STM32/cơ cấu có hoàn thành không; timeout có đủ không; không tự gửi lại |
| Thấy dòng chào STM32 nhưng PING lỗi | Dòng chào chỉ chứng minh có dữ liệu nhận, chưa chứng minh parser và chiều truyền Pi→STM32 hoạt động |
| `BAD_RUBIK_MOVE_ARG` | Firmware phải hỗ trợ token được gửi; LR/UD và dạng ghép hiện chưa hỗ trợ |
| `Solution does not solve...` | Công thức không khớp cube; kiểm tra dữ liệu đã lưu và chiều/hướng mặt |
| GUI lỗi display/Tcl | Chạy trong Desktop/VNC; kiểm tra `python3-tk`; CLI vẫn dùng được qua SSH |
| Auto Solve báo SCAN_POSE | Giới hạn hiện tại của firmware; dùng quét thủ công và run_solver.py |
| Servo xoay nhưng cube không đúng | Đối chiếu hướng đặt khối, quy ước mặt, chiều xoay và dữ liệu quét thực tế |

## 14. Trình tự chạy hằng ngày

1. Vào thư mục dự án và dùng Python trong `.venv-pi`.
2. Kiểm tra PING bằng terminal UART, rồi thoát terminal đó.
3. Chuẩn bị cơ cấu; RESET nếu cần và đã sẵn sàng thực hiện bước này.
4. Quét thủ công hoặc nhập trạng thái cube hiện tại, đặt khối đúng hướng máy.
5. Chạy `run_solver.py` không có `--port` để xem trước và kiểm tra dữ liệu.
6. Chạy lại với `--port /dev/serial0` để thực thi, theo dõi OK/DONE và tiến độ.
7. Nếu có lỗi, kiểm tra trạng thái thật trước lần gửi kế tiếp.

Tài liệu liên quan: [ghi chú UART solver](docs/solver_uart.md), [module Rubik_Cube](rpi/Rubik_Cube/README.md), [handler STM32](firmware/rubik_stm32_ver1/Hardware/UART_Handle/Rubik_Command.c), [session UART Python](rpi/Rubik_Cube/UART_Command/session.py).
