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

```bash
cd rpi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m rubik_robot.main --mode demo
python -m unittest discover tests
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
