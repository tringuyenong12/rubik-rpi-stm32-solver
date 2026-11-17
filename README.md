# Rubik RPi STM32 Solver

Hệ thống giải Rubik 3x3x3 dùng Raspberry Pi 4 để xử lý ảnh và tìm lời giải, STM32 để điều khiển servo/driver cơ cấu kẹp xoay.

## Mục Tiêu

- Ghi nhận 6 mặt Rubik bằng camera.
- Phân loại màu và chuẩn hóa trạng thái cube theo định dạng solver.
- Kiểm tra trạng thái hợp lệ trước khi giải.
- Tìm chuỗi bước giải bằng solver 2-phase/Kociemba.
- Biến chuỗi bước `R U R' U' ...` thành lệnh servo/motion.
- Gửi lệnh từ Raspberry Pi 4 sang STM32 qua UART.
- STM32 điều khiển servo theo chuỗi lệnh an toàn, có ACK/NACK và trạng thái lỗi.

## Chức Năng Bắt Buộc

1. Giải Rubik 3x3x3 tự động.
   - Hệ thống tự scan trạng thái Rubik, tìm lời giải, lập kế hoạch chuyển động và điều khiển servo để giải cube.

2. Tạo đề bài trộn Rubik theo mức độ.
   - Phần mềm sinh chuỗi trộn Rubik theo các cấp độ, ví dụ dễ, trung bình, khó.
   - Mỗi đề bài cần lưu được scramble, trạng thái cube sau khi trộn và đáp án giải.

3. Hướng dẫn giải và hiển thị các bước giải Rubik cho người chơi.
   - Giao diện/CLI hiển thị từng bước giải theo ký hiệu Rubik.
   - Có thể hiển thị mô tả dễ hiểu cho người mới, ví dụ xoay mặt nào, theo chiều nào, bao nhiêu lần.
   - Chức năng này dùng chung solver với chế độ giải tự động, nhưng đầu ra là hướng dẫn cho người chơi thay vì lệnh servo.

## Kiến Trúc Nhanh

```text
Camera
  -> Raspberry Pi 4
      -> Vision: capture, perspective correction, color classification
      -> Cube state validation
      -> Solver: Kociemba / 2-phase
      -> Motion planner: cube moves -> robot actions
      -> UART protocol
  -> STM32
      -> Command parser
      -> Servo scheduler
      -> Safety timeout / homing
  -> Servo + cơ cấu kẹp/xoay Rubik
```

## Cấu Trúc Repo

```text
docs/                   Tài liệu plan, kiến trúc, giao tiếp, pipeline CV
rpi/                    Code chạy trên Raspberry Pi 4
  rubik_robot/          Package điều khiển robot chính (Vision, State, Motion, Transport)
  twophase/             Package giải Rubik 2-Phase thuần Python (Herbert Kociemba) tích hợp sẵn
firmware/stm32cubeide/  Firmware STM32 theo workflow STM32CubeIDE/CubeMX
mechanical/             Ghi chú cơ khí, calibration và test motion
technical drawing/      Ảnh bản vẽ/CAD của thiết kế cơ khí hiện tại
calibration/            Nơi lưu thông số màu/servo theo phần cứng thực
scripts/                Script tiện ích cho demo/test (demo_pipeline.py, run_vision_gui.py)
```

## Quick Start Cho Raspberry Pi

Hướng dẫn này dùng Raspberry Pi OS Desktop 64-bit, Python từ 3.10 và camera USB.
Các lệnh cài thư viện, kiểm tra môi trường và chạy ứng dụng được tổng hợp trong
[INSTALL_PI.txt](INSTALL_PI.txt). Chạy các lệnh dưới đây trên Pi, từ thư mục dự án
đã chép vào `/home/nguy3n/rubik-rpi-stm32-solver`.

OpenCV (`cv2`), NumPy, pyserial (`serial`) và Tkinter là các thư viện chạy ứng dụng.
APT cài các bản do Raspberry Pi OS cung cấp cùng phụ thuộc hệ thống. Môi trường
`.venv-pi` dùng `--system-site-packages` để truy cập các gói này theo hướng dẫn của
[Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html).
Bộ giải Two-Phase đã nằm trong `rpi/twophase`; `kociemba` là dự phòng tùy chọn.

```bash
sudo apt update
sudo apt install -y python3-venv python3-opencv python3-numpy python3-serial python3-tk python3-pytest v4l-utils
cd ~/rubik-rpi-stm32-solver
python3 -m venv --system-site-packages .venv-pi
.venv-pi/bin/python -c 'import cv2, numpy, serial, tkinter; print("Thu vien OK")'
```

Terminal thứ nhất chạy server trên Pi. Giữ terminal mở và đợi thông báo
`Server now listening...`. Lần đầu có thể mất thời gian tạo bảng tra solver.

```bash
cd ~/rubik-rpi-stm32-solver
.venv-pi/bin/python -u -B rpi/twophase/start_server.py 8080 20 3
```

Ba tham số lần lượt là cổng TCP `8080`, số nước tối đa `20` và thời gian tìm kiếm
yêu cầu `3` giây. Terminal thứ hai trên Desktop của Pi hoặc trong phiên VNC chạy
giao diện quét màu và hướng dẫn giải.

```bash
cd ~/rubik-rpi-stm32-solver
.venv-pi/bin/python -B scripts/run_vision_gui.py --camera 0 --backend auto
```

Dùng `v4l2-ctl --list-devices` để xem camera USB, thử `--camera 1` nếu cần.
Đường dẫn `.venv\Scripts\python.exe` và backend `dshow` thuộc Windows.
Môi trường `.venv-pi` được tạo riêng trên Pi. GUI cần phiên Desktop có màn hình;
server có thể chạy qua SSH. Camera CSI cắm cáp dẹt cần kiểm tra đường lấy ảnh riêng.

Thông số trong `calibration/camera_settings.json` và `calibration/camera_roi.json`
lưu theo chỉ số camera. Bản hiệu chỉnh hiện tại dùng camera `1` trên Windows;
khi Pi dùng camera `0`, cần hiệu chỉnh cho chỉ số `0`. Phơi sáng/cân bằng trắng
phụ thuộc driver Linux. Chọn lại ROI bằng phím `P` khi đổi vị trí lắp camera.

Để chạy demo hoặc kiểm thử từ thư mục `rpi` trên Pi dùng các lệnh sau.

```bash
cd ~/rubik-rpi-stm32-solver/rpi
../.venv-pi/bin/python -m rubik_robot.main --mode demo
../.venv-pi/bin/python -m unittest discover -s tests
```

Trên Windows PowerShell:

```powershell
cd rpi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m rubik_robot.main --mode demo
python -m unittest discover tests
```

Theo mapping cơ khí mới, CLI mặc định xuất lệnh xoay mặt bằng `TURN`. Nếu muốn test firmware cũ với lệnh `MOVE`:

```bash
python -m rubik_robot.main --mode demo --face-turn-command MOVE
```

Nếu muốn cài package ở chế độ editable:

```bash
cd rpi
pip install -e .
rubik-robot --mode demo
```

## Quick Start Cho STM32CubeIDE

Firmware được tổ chức theo STM32CubeIDE/CubeMX. Tạo project CubeIDE, cấu hình UART + TIM PWM, sau đó copy `firmware/stm32cubeide/App` vào project.

Mặc định firmware nhận frame UART dạng ASCII:

```text
MOVE U 1 400
MOVE R -1 400
HOME
PING
```

Xem chi tiết trong [docs/CUBEIDE_SETUP.md](docs/CUBEIDE_SETUP.md) và [docs/UART_PROTOCOL.md](docs/UART_PROTOCOL.md).

## Roadmap

1. Demo pipeline bằng ảnh mẫu tĩnh: nhận diện 54 stickers và sinh cube string.
2. Giải cube string bằng solver và in chuỗi bước.
3. Mô phỏng motion planner, đếm số thao tác servo.
4. Chạy UART loopback RPi <-> STM32.
5. Điều khiển từng servo riêng, calibration góc.
6. Chạy full cycle với Rubik thật.

Chi tiết nằm trong [docs/PLAN.md](docs/PLAN.md).

Danh sách vật tư gợi ý nằm trong [docs/BOM.md](docs/BOM.md).

Thiết kế cơ khí theo bản vẽ CAD được tổng hợp trong [docs/MECHANICAL_DESIGN.md](docs/MECHANICAL_DESIGN.md) và mapping actuator trong [docs/ACTUATOR_MAPPING.md](docs/ACTUATOR_MAPPING.md).

## Trạng Thái Hiện Tại

Repo này là bộ khung ban đầu cho đồ án. Code Python có demo solver/motion/protocol, firmware STM32 có parser lệnh cơ bản. Các thông số camera, màu, servo và cơ khí cần được calibration theo phần cứng thực tế.

## Quét Camera Và Hướng Dẫn Trên Client–Server

Chạy các lệnh dưới đây từ thư mục gốc project, với môi trường Python ở `.venv`.

Terminal thứ nhất chạy server Two-Phase.

Server là tùy chọn khi hostname là `localhost`, `127.0.0.1` hoặc `::1`: nếu
kết nối bị từ chối vì server chưa chạy, client tự dùng solver có sẵn trên máy
trong luồng nền. Sáu mặt đã quét được giữ nguyên; không cần quét lại vì lỗi
kết nối. Server từ xa vẫn yêu cầu đúng hostname và cổng đang hoạt động.

```powershell
.\.venv\Scripts\python.exe -B rpi\twophase\start_server.py 8080 20 3
```

Terminal thứ hai mở Solver Client và Logitech ID 1.

```powershell
.\.venv\Scripts\python.exe -B scripts\run_vision_gui.py --camera 1 --backend dshow
```

- Bật `Auto scan` và `Auto solve after 6 faces`. Giữ mỗi mặt ngay ngắn để tự lưu, có thể quét khác thứ tự.

  Khi mở camera, chờ 2 giây để phơi sáng/cân bằng trắng ổn định; trong thời gian
  này chỉ hiện ROI, không phân loại hoặc lưu màu tạm thời. Auto scan sau đó
  chờ ít nhất 1,5 giây và 12 mẫu, kiểm tra độ ổn định màu tâm trước
  khi lưu. Sau mỗi lần lưu, cần chuyển rõ sang mặt khác; chỉ đổi nhãn màu tâm
  trong khi các ô còn lại giống mặt đã lưu sẽ bị chặn. Nếu tâm đang gần ranh
  giới hai màu, chương trình chờ ảnh rõ hơn. Dùng `Rescan shown face` để chủ động
  quét lại mặt hiện tại; thao tác này mở lại bộ đếm giữ yên cho mặt đó.
- Quy ước tâm là U vàng, R xanh lá, F đỏ, D trắng, L xanh biển, B cam. Khi quét U, cạnh trên giáp cam. Khi quét D, cạnh trên giáp đỏ. Bốn mặt bên có cạnh trên giáp vàng.
- Đủ sáu mặt, client kiểm tra mỗi màu đủ 9 ô và tìm hướng mặt hợp lệ. Màu lưu phải khớp nhãn đã ổn định và lần đọc camera mới nhất. Chương trình không tự đổi màu để cân đủ số lượng hoặc tạo trạng thái hợp lệ; dữ liệu còn sai/mơ hồ sẽ không xuất công thức. Có thể sửa ô ngay cả sau thông báo lỗi hoặc dùng `Rescan shown face`, rồi `Solve`.
- Sau khi giải, cửa sổ riêng hiển thị toàn bộ công thức và hình minh họa từng nước. Camera chỉ quét màu, không vẽ mũi tên hoặc xác nhận bước giải.
- Giữ **F đỏ hướng về phía bạn, U vàng ở trên, R xanh lá bên phải** trong suốt công thức. Hình minh họa có sơ đồ sáu mặt và hình phóng to mặt cần xoay. Chiều kim đồng hồ luôn tính khi nhìn thẳng vào chính mặt đang xoay; B nhìn từ phía sau, D nhìn từ phía dưới.
- `F`, `U`, `R`, `L`, `B`, `D`: xoay 90° cùng chiều; dấu `'`: ngược chiều; `2`: 180° trong một bước. Dùng **Bước trước/Bước tiếp** hoặc phím trái/phải để tự chuyển; việc xem hết công thức không phải xác nhận Rubik thực tế đã giải xong.
- **Sao chép công thức** sao chép chuỗi nước giải. **Lưu hướng dẫn .html** xuất công thức và hình SVG của từng nước trong một file mở ngoại tuyến. Đóng cửa sổ hình rồi có thể mở lại bằng **Xem công thức và hình hướng dẫn**.
- `New scan` hủy hướng dẫn và bắt đầu quét lại. `--show-masks` mở thêm bộ lọc để hiệu chỉnh màu.

Có thể mở lại công thức đã lưu bằng `--restore-solution duong_dan.json`; file
JSON gồm `cube` (chuỗi 54 ô của lượt quét) và `solution` (công thức). Chương trình
kiểm tra lời giải hợp lệ trước khi nạp lại; đây là lượt quét đã lưu, không phải
xác nhận trạng thái vật lý hiện tại của Rubik.

### Vùng nhận diện ROI

Camera chỉ tìm ô màu trong khung ROI màu vàng, mặc định là vùng vuông ở giữa ảnh.
Đặt trọn mặt Rubik (đủ 9 ô) trong khung. Nhấn giữ chuột trái và kéo từ một góc
đến góc đối diện để chỉnh ROI sát quanh mặt Rubik, chừa một ít khoảng trống quanh
viền. Vùng ngoài ROI được làm tối trên ảnh xem trước và không tham gia nhận diện.

Nhấn `R` trong cửa sổ `Rubik Cube Detection` để đưa ROI về mặc định. ROI được tự
lưu riêng theo chỉ số camera tại `calibration/camera_roi.json`, tự co giãn theo
độ phân giải ảnh và dùng chung cho `Solve Guide` và `Auto Solve`. Chỉnh vùng bằng
cửa sổ camera của `Solve Guide` trước khi bắt đầu `Auto Solve`.

Nếu camera nhìn mặt Rubik nghiêng, nhấn `P` rồi bấm bốn góc ngoài của mặt theo
thứ tự góc trên trái, trên phải, dưới phải, dưới trái của mặt Rubik. Với ảnh dạng
hình thoi, có thể chọn lần lượt đỉnh trên, phải, dưới, trái. Chương trình nắn ảnh
về mặt vuông và lấy mẫu ở tâm từng ô, tránh viền và chi tiết máy. Giữ vị trí mặt
Rubik ổn định trong vùng đã chọn; khi đổi vị trí camera hoặc gá máy cần chọn lại.
Khung ROI hiển thị được nới thêm khoảng 9% mỗi cạnh quanh bốn góc đã chọn,
giữ dạng vuông theo mặt Rubik (nhìn nghiêng có thể thành hình thoi).
Các điểm lấy mẫu vẫn nằm trong mặt Rubik; nếu lần đọc đầu không hợp lệ,
chương trình thử dịch lưới nhẹ trong vùng đệm để chịu được sai lệch vị trí nhỏ.
Thứ tự góc quyết định thứ tự chín ô được đọc, nên cần chọn đúng hướng trên của mặt.

Thông số riêng của camera được đọc từ `calibration/camera_settings.json`, gồm
`capture` (phơi sáng, gain, cân bằng trắng) và `vision` (ngưỡng HSV). Cấu hình
được áp dụng khi mở camera cho cả hai chế độ; khởi động lại để nạp thay đổi.
Camera không hỗ trợ một thuộc tính có thể từ chối lệnh; terminal in giá trị yêu
cầu, kết quả đặt và giá trị đọc lại để kiểm tra.

Để ghi ảnh gốc phục vụ kiểm thử lặp lại, thêm
`--diagnostics artifacts/camera_tuning/ten_lan_thu` vào lệnh mở client (tối đa 480
ảnh, cách nhau ít nhất 0,25 giây). Dùng thư mục mới cho mỗi lần thử. Công cụ
`scripts/tune_camera.py` thử các mức phơi sáng/gain khi client đã đóng;
`scripts/evaluate_vision.py` đối chiếu ảnh đã ghi với các đoạn giữ yên được gán
nhãn độc lập. Không tính những ảnh đang xoay hoặc bị tay che vào độ chính xác
của các đoạn giữ yên.

Để đo độ mượt ngay trong ứng dụng, thêm
`--performance artifacts/camera_tuning/ten_lan_do.json`. Số liệu thời gian xử lý,
FPS, nhãn màu và một số ảnh nhỏ được giữ trong RAM rồi ghi khi đóng camera;
không ghi ảnh liên tục vào ổ đĩa trong lúc đo. Công cụ
`scripts/benchmark_camera.py --seconds 10 --output artifacts/camera_tuning/benchmark.json`
đo riêng đọc camera, nhận diện, vẽ và hiển thị khi client đã đóng. Luồng nhận
diện chỉ tính HSV một lần cho ảnh nắn, bỏ bộ lọc debug khi không bật
`--show-masks`, dùng mặt nạ ROI được lưu đệm và giới hạn OpenCV ở hai luồng để
giảm các khung hình chậm bất thường.

Nhãn trên camera cần ít nhất ba lần đọc và đồng thuận trong cửa sổ năm mẫu.
Một lần đọc hụt ngắn được giữ nhãn tối đa 0,18 giây; khi thấy ảnh đang chuyển
động hoặc đổi mặt, nhãn cũ được xóa và thu lại. Khung đánh dấu cùng mặt được
giữ vị trí để không nhảy theo mỗi lần dò lệch ROI. Bộ lọc này chỉ ổn định hình
hiển thị; dữ liệu dùng để lưu mặt vẫn là mẫu camera mới và điều kiện giữ yên
1,5 giây, không lấy nhãn cũ từ ảnh xem trước để tự lưu.

Ô xanh bị phản sáng có thể trông gần trắng. Khi mẫu còn ám xanh hoặc vùng
xung quanh tâm vẫn có sắc xanh rõ, chương trình thử vị trí lấy mẫu khác trong
cùng ô; nếu chưa chắc chắn thì chờ, không lưu thành trắng. Đổi màu một ô liên
tục cũng khởi động lại thời gian giữ để tránh lưu một màu chỉ xuất hiện thoáng qua.
`calibration/last_camera_scan.json` ghi đúng màu/HSV đã lưu;
`calibration/last_solver_input.json` ghi các mặt đầu vào, chuỗi cube thực sự
đưa sang solver hoặc lý do từ chối. Solver chỉ được phép xoay hướng lưới mặt,
không được thay màu các ô so với dữ liệu đã lưu.

Chạy bộ kiểm thử Python từ thư mục gốc.

```powershell
Push-Location rpi
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
Pop-Location
```

## Trộn Bộ Đề Từ Rubik Đã Giải

Trong Solver Client, chọn tab `Scramble` ở thanh lựa chọn phía trên để mở chức năng trộn.

| Mức độ | Số nước trộn |
| --- | --- |
| Dễ | 5 |
| Trung bình | 12 |
| Khó | 22 |

Mức độ được chia theo độ dài chuỗi sinh ra. Mỗi bộ đề được tính từ trạng thái đã giải, tránh hai nước liên tiếp trên cùng trục. Độ dài lời giải tối ưu của bộ đề có thể khác số nước trộn.

1. Đặt Rubik đã giải theo U vàng, F đỏ, R xanh lá.
2. Chọn `Easy`, `Medium` hoặc `Hard`, rồi bấm `Generate scramble` để xem chuỗi xoay, lệnh UART và sơ đồ sáu mặt của trạng thái đích.
3. Dùng `Copy UART` hoặc `Save .txt` để xuất đúng các bước trộn.
4. Chọn cổng COM, baud rate và bấm `Send UART` để gửi trực tiếp.
5. Mỗi lệnh `TURN` chờ `OK TURN` rồi `DONE TURN`. Lỗi hoặc timeout sẽ dừng chuỗi và báo số bước đã xác nhận. Nút dừng chờ bước đang chạy hoàn tất rồi ngừng gửi các bước tiếp theo.

Trước mỗi lần gửi lại hoặc tạo bộ đề mới để thực hiện trên robot, đưa Rubik về trạng thái đã giải. Chuyển về `Solve Guide` sẽ mở một lượt quét mới. Khi firmware báo `ERR UNSUPPORTED`, cần triển khai sequence xoay tương ứng để thực thi lệnh đã xuất. Giao thức chi tiết nằm trong [UART_PROTOCOL.md](docs/UART_PROTOCOL.md).

Tạo và xuất bộ đề bằng terminal từ thư mục gốc project.

```powershell
.\.venv\Scripts\python.exe -B scripts\run_scramble.py --level easy
.\.venv\Scripts\python.exe -B scripts\run_scramble.py --level medium
.\.venv\Scripts\python.exe -B scripts\run_scramble.py --level hard --output scramble_hard.txt
```

Gửi trực tiếp qua cổng COM đã chọn.

```powershell
.\.venv\Scripts\python.exe -B scripts\run_scramble.py --level easy --port COM5 --baudrate 115200
```

`--seed 7` tái tạo cùng bộ đề để kiểm thử. `--duration-ms` và `--face-turn-command` điều chỉnh thời gian hoặc chọn `MOVE` cho firmware tương ứng.

## Tự Động Quét Và Giải Qua UART

Chọn tab thứ ba `Auto Solve` trong cùng Solver Client. Đặt Rubik xáo trộn vào
máy với hướng màu bất kỳ, chọn cổng UART và bấm `Start`. Camera nhận diện mặt
đầu tiên tại chỗ và cập nhật theo màu tâm trước khi kết nối UART.

Chương trình gửi bảy tư thế `SCAN_POSE` cố định sau lần chụp đầu, chờ `DONE` rồi
tự chụp các phía còn lại. U/F/D/B/R/L biểu thị vị trí của khối trong máy lúc Start.
Các mặt xuất hiện dần theo màu tâm, có kiểm tra trùng. Đủ sáu mặt sẽ thông báo,
đưa khối về tư thế ban đầu, kiểm tra trạng thái, gọi server Two-Phase và xuất/gửi
từng lệnh giải `TURN` theo hệ tọa độ máy qua UART. Nút dừng ngừng các bước tiếp
theo sau thao tác hiện tại.

Lệnh mở server và client vẫn giống phần hướng dẫn giải phía trên. Firmware cần
thực hiện đúng hợp đồng tư thế toàn khối và trả `DONE`; firmware hiện có thể trả
`ERR UNSUPPORTED` khi sequence cơ khí chưa được triển khai. Phần mới chỉ xử lý
camera, solver và UART ở PC. Hướng đặt camera, bảng tư thế, phản hồi và lệnh kiểm
thử đầy đủ nằm trong [AUTO_SOLVE.md](docs/AUTO_SOLVE.md).
