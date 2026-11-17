# Kiến Trúc Hệ Thống

## Data Flow

```text
capture images
  -> sticker extraction
  -> color classification
  -> cube state
  -> state validation
  -> solver moves
  -> robot actions
  -> UART frames
  -> STM32 servo scheduler
```

## Cơ Khí Theo Bản Vẽ Hiện Tại

Theo các ảnh CAD trong `technical drawing/`, hệ thống nên được coi là robot có:

- Camera cố định trên khung nhôm, nhìn từ trên xuống.
- 4 cụm actuator trượt chéo quanh Rubik.
- Cụm giữ/xoay gần cube.
- Cụm trung tâm dưới mặt bàn có khả năng nâng/xoay/định vị.

Vì vậy kiến trúc điều khiển nên tách thành 2 lớp:

1. `cube move planner`: xử lý các bước Rubik `U R F D L B`.
2. `machine action planner`: chuyển các bước Rubik thành action theo actuator thực tế như `approach`, `clamp`, `turn`, `release`, `retract`.

Chi tiết nằm trong [MECHANICAL_DESIGN.md](MECHANICAL_DESIGN.md) và [ACTUATOR_MAPPING.md](ACTUATOR_MAPPING.md).

## Raspberry Pi 4

### Vision

Trách nhiệm:

- Lấy ảnh từ camera.
- Cắt vùng Rubik / tìm lưới 9 ô sticker.
- Lấy màu trung bình của 9 sticker (qua CIELAB hoặc HSV filter).
- Phân loại màu theo calibration.
- Sinh cube string theo thứ tự solver (`URFDLB`).
- Hỗ trợ công cụ tinh chỉnh tương tác webcam qua `twophase.vision2` và `twophase.client_gui2`.

File liên quan:

- `rpi/rubik_robot/vision/capture.py`
- `rpi/rubik_robot/vision/color_classifier.py`
- `rpi/twophase/vision2.py`
- `rpi/twophase/vision_params.py`
- `rpi/twophase/client_gui2.py`
- `scripts/run_vision_gui.py`
- `rpi/rubik_robot/cube/state.py`

### Solver

Trách nhiệm:

- Nhận cube string 54 ký tự định dạng `URFDLB`.
- Kiểm tra tính hợp lệ cơ bản (đúng 54 ô, mỗi mặt đúng 9 ô).
- Gọi thuật toán Two-Phase thuần Python từ package tích hợp sẵn `rpi/twophase` (Herbert Kociemba 2-phase algorithm) với các bảng pruning table nạp cực nhanh.
- Chuẩn hóa đầu ra từ ký hiệu numbered (`R1, R2, R3`) sang chuẩn xoay Rubik (`R, R2, R'`).
- Có fallback sang thư viện C `kociemba` nếu cần.

File liên quan:

- `rpi/twophase/` (Gói solver Two-Phase độc lập)
- `rpi/rubik_robot/solver/kociemba_solver.py` (Adapter kết nối solver với robot)


### Motion Planner

Trách nhiệm:

- Chuyển cube moves thành robot actions.
- Ước lượng cost cho từng chuỗi action.
- Là nơi mở rộng để tối ưu "hướng giải nhanh nhất" theo cơ khí thực tế.
- Với bản vẽ hiện tại, motion planner phải tính thêm cost cho 4 cụm trượt chéo và cụm trung tâm, không chỉ đếm số bước Rubik.

File liên quan:

- `rpi/rubik_robot/motion/planner.py`

### Transport

Trách nhiệm:

- Đóng gói lệnh ASCII.
- Gửi qua UART.
- Đợi ACK/NACK và retry.

File liên quan:

- `rpi/rubik_robot/transport/serial_link.py`
- `rpi/rubik_robot/protocol.py`

## STM32

STM32 nên chỉ làm các việc thời gian thực, đơn giản và chắc chắn:

- Nhận lệnh UART.
- Parse lệnh.
- Điều khiển PWM servo.
- Quản lý trạng thái `IDLE`, `BUSY`, `ERROR`, `STOPPED`.
- Trả lời `OK`, `ERR`, `DONE`.

Không nên đưa solver hoặc xử lý ảnh vào STM32.

## Chuỗi Trạng Thái Đề Xuất

```text
BOOT
  -> IDLE
  -> HOMING
  -> IDLE
  -> EXECUTING_MOVE
  -> IDLE
  -> ERROR or STOPPED
```

## Tối Ưu Hướng Giải Nhanh

Kociemba tối ưu số bước cube, nhưng robot cần tối ưu thời gian cơ khí. Nên tách thành 2 tầng:

1. Solver sinh một hoặc nhiều solution ứng viên.
2. Motion planner tính cost robot cho từng solution/hướng đặt cube.

Cost có thể gồm:

- Số lần reorient cube.
- Số lần grip/release.
- Tổng góc quay servo.
- Delay an toàn.
- Penalty cho mặt khó thao tác.

Ban đầu có thể chọn solution đầu tiên. Khi có hardware thật, cập nhật cost model theo thời gian đo được.
