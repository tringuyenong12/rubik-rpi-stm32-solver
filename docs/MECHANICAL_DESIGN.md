# Thiết Kế Cơ Khí Theo Bản Vẽ

Tài liệu này tổng hợp từ các ảnh CAD trong thư mục `technical drawing/`. Một số điểm bên dưới là suy luận từ hình ảnh, cần xác nhận lại bằng kích thước và danh sách linh kiện thực tế.

## Tổng Quan

Thiết kế hiện tại phù hợp với cấu trúc robot giải Rubik dạng bàn máy cố định:

- Camera đặt trên khung nhôm định hình, nhìn xuống Rubik từ phía trên.
- Rubik nằm ở trung tâm bàn máy.
- Bốn cụm tác động bố trí chéo quanh Rubik theo dạng chữ X.
- Mỗi cụm có ray trượt/linear rail và cơ cấu rack-pinion để tiến/lùi vào Rubik.
- Gần trung tâm có các cụm kẹp/giữ mặt cube.
- Dưới mặt bàn có một cụm cơ khí trung tâm, có khả năng là cơ cấu nâng, xoay hoặc định vị cube.
- Khung dưới và mặt bàn tạo thành một module có thể đặt STM32, driver, nguồn servo/motor.

## Các Cụm Chính

### 1. Cụm Camera Trên Cao

Quan sát từ ảnh:

- Khung nhôm định hình đứng + ngang tạo cần gắn camera.
- Camera hướng xuống vùng Rubik.
- Vị trí camera cố định, phù hợp với pipeline grid cố định.

Ý nghĩa cho phần mềm:

- Pipeline thị giác có thể ưu tiên `fixed_grid_scan`.
- Nên calibration một lần các điểm 9 sticker trên ảnh, sau đó lưu vào `calibration/color_profile.json`.
- Cần thêm bước kiểm tra cube có nằm đúng tâm trước khi phân loại màu.

### 2. Bốn Cụm Trượt Chéo

Quan sát từ ảnh top view:

- Có 4 cụm ray trượt đặt chéo vào tâm cube.
- Mỗi cụm có bàn trượt và cơ cấu bánh răng/thanh răng.
- Các cụm này có thể dùng để đưa đầu kẹp/đầu xoay vào mặt Rubik.

Đặt tên trong repo:

```text
carriage_nw
carriage_ne
carriage_sw
carriage_se
```

Trong đó `nw/ne/sw/se` là cách đặt tên theo góc nhìn từ camera top-down, chưa phải tọa độ vật lý bắt buộc.

Ý nghĩa cho firmware:

- Nếu dùng servo liên tục/DC motor/stepper cho rack-pinion, cần driver riêng và cảm biến hành trình.
- Nếu dùng servo góc cho cơ cấu gắn trên carriage, cần thêm kênh PWM.
- STM32 nên quản lý từng cụm như một actuator có trạng thái: `HOME`, `APPROACH`, `ENGAGED`, `RETRACTED`, `ERROR`.

### 3. Cụm Giữ/Xoay Gần Cube

Quan sát từ ảnh:

- Có các chi tiết màu nâu đặt quanh cube, giống cụm kẹp/giữ mặt.
- Các cụm này có thể giữ cube trong lúc mặt khác xoay, hoặc định vị cube khi scan.

Ý nghĩa cho motion planner:

- Không nên map trực tiếp mỗi move `R/U/F/...` thành một servo duy nhất.
- Nên có lớp trung gian: `cube move -> robot action sequence`.
- Robot action có thể gồm: `approach`, `clamp`, `turn_face`, `release`, `retract`, `reorient`.

### 4. Cụm Trung Tâm Dưới Mặt Bàn

Quan sát từ ảnh:

- Dưới mặt bàn có một module màu xanh/đỏ/xanh dương, liên kết với trục/gear ở trung tâm.
- Có khả năng là cơ cấu nâng, xoay cube, hoặc hỗ trợ scan/căn chỉnh vị trí.

Ý nghĩa cho firmware:

- Cần tách actuator trung tâm thành các role riêng, ví dụ:
  - `center_lift`
  - `center_rotate`
  - `center_lock`
- Nếu dùng cơ cấu này để đổi hướng cube, motion planner phải tính cost cho thao tác reorient.

## Kiến Trúc Điều Khiển Phù Hợp

Thay vì coi STM32 chỉ điều khiển 4 servo, repo nên theo cấu trúc:

```text
RPi solver
  -> cube moves
  -> machine action planner
  -> high-level UART commands
STM32
  -> actuator state machine
  -> servo PWM / motor driver / limit switch
  -> ACK / DONE / ERR
```

## Các Thông Tin Cần Xác Nhận

Để chốt mapping chính xác, cần bổ sung:

- Mỗi cụm trượt dùng motor gì: servo góc, servo liên tục, DC gear motor hay stepper.
- Có cảm biến hành trình/home switch không.
- Có bao nhiêu kênh servo tổng cộng.
- Cụm trung tâm dưới mặt bàn có chức năng chính xác là nâng, xoay, hay cả hai.
- Các đầu kẹp có thể xoay mặt Rubik 90/180 độ trực tiếp hay chỉ giữ cube.
- Cube được scan bằng camera một lần từ trên, hay robot sẽ xoay cube để chụp đủ 6 mặt.

## Quyết Định Thiết Kế Trong Repo

Theo bản vẽ, repo sẽ ưu tiên phương án:

- Camera cố định trên cao.
- Bốn cụm actuator chéo quanh cube.
- STM32 điều khiển actuator theo state machine.
- RPi vẫn giữ vai trò vision, solver, tạo đề bài, hướng dẫn giải và motion planning.
- Giao thức UART mở rộng dần từ lệnh debug `SERVO` sang các lệnh high-level như `ACTUATOR`, `CLAMP`, `TURN`, `SCAN_POSE`.
