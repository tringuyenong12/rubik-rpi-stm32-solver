# Kế Hoạch Đồ Án: Hệ Thống Giải Rubik 3x3x3

## 1. Phạm Vi

Hệ thống gồm 3 khối chính:

- Raspberry Pi 4: camera, xử lý ảnh, solver, motion planner, giao tiếp UART.
- STM32: nhận lệnh, điều khiển servo, phản hồi trạng thái, bảo vệ timeout.
- Cơ khí: khung giữ Rubik, servo kẹp/xoay, camera mount, đèn chiếu sáng ổn định.

Mục tiêu thực tế nên là "giải ổn định" trước, sau đó mới tối ưu tốc độ.

## 2. Yêu Cầu Chức Năng

- Chức năng 1: Giải Rubik 3x3x3 tự động.
  - Quét trạng thái Rubik bằng camera.
  - Phân loại màu và tạo cube string.
  - Tìm lời giải bằng solver.
  - Chuyển lời giải thành chuỗi action robot.
  - Gửi lệnh cho STM32 điều khiển servo để giải Rubik.

- Chức năng 2: Tạo đề bài trộn Rubik theo mức độ.
  - Sinh scramble theo mức độ `de`, `trung_binh`, `kho`.
  - Đảm bảo scramble hợp lệ và có thể giải ngược lại.
  - Lưu thông tin đề bài: tên mức độ, chuỗi trộn, cube state sau khi trộn, lời giải mẫu.
  - Có thể dùng cho chế độ luyện tập hoặc demo.

- Chức năng 3: Hướng dẫn giải và hiển thị các bước giải Rubik cho người chơi.
  - Hiển thị chuỗi bước giải theo ký hiệu Rubik, ví dụ `R U R' U'`.
  - Giải thích từng bước bằng ngôn ngữ dễ hiểu.
  - Cho phép người chơi xem từng bước, quay lại bước trước, hoặc xem toàn bộ lời giải.
  - Tái sử dụng solver của chế độ tự động, nhưng không gửi lệnh servo nếu người dùng chỉ muốn học/cầm tay giải.

## 3. Yêu Cầu Chức Năng Chi Tiết Cho Chế Độ Tự Động

- Quét đủ 6 mặt Rubik hoặc chụp 6 hướng của cube.
- Phân loại 6 màu: W, Y, R, O, B, G.
- Sinh cube string 54 ký tự theo thứ tự `URFDLB`.
- Kiểm tra trạng thái: đúng 9 sticker/màu, center hợp lệ, solver chấp nhận.
- Tìm lời giải.
- Chuyển lời giải thành lệnh robot.
- STM32 thực thi lệnh và báo ACK/NACK.
- Cơ chế dừng khẩn cấp bằng nút bấm hoặc lệnh `STOP`.

## 4. Yêu Cầu Phi Chức Năng

- Ảnh chụp ổn định dưới cùng một nguồn sáng.
- Sai số servo được calibration riêng cho từng trục.
- Sau mỗi lệnh quan trọng có xác nhận trạng thái.
- Log đầy đủ: ảnh đầu vào, màu đã phân loại, cube string, solution, action list, UART transcript.

## 5. Đề Xuất Phần Cứng

- Raspberry Pi 4, camera module hoặc USB camera.
- STM32F103/STM32F401/STM32F411 hoặc board tương đương có timer PWM.
- Servo MG996R/DS3218 cho trục cần moment lớn.
- Nguồn servo riêng 5-6V, dòng đủ lớn; nối chung GND với STM32/RPi.
- Đèn LED vòng hoặc LED panel để giảm bóng đổ.
- Nút E-STOP cắt tín hiệu enable servo hoặc cắt nguồn servo.

## 6. Kiến Trúc Cơ Khí Theo Bản Vẽ

Theo các ảnh CAD đã thêm vào repo, phương án cơ khí hiện tại là:

- Camera gắn trên khung nhôm cao, nhìn xuống cube.
- 4 cụm trượt chéo quanh cube, có cơ cấu rack-pinion.
- Các đầu tác động/giữ mặt cube nằm gần trung tâm.
- Cụm trung tâm dưới mặt bàn có khả năng nâng/xoay/định vị cube.

Vì vậy repo sẽ ưu tiên motion planner theo actuator role thay vì phương án 2 kẹp đơn giản. Chi tiết nằm trong [MECHANICAL_DESIGN.md](MECHANICAL_DESIGN.md) và [ACTUATOR_MAPPING.md](ACTUATOR_MAPPING.md).

## 7. Các Mốc Thực Hiện

### Giai Đoạn 1: Nền Tảng

- Tạo repo, chuẩn code, docs.
- Chạy demo solver bằng cube state có sẵn.
- Tạo UART protocol và loopback test.
- Viết firmware nhận `PING`, `HOME`, `MOVE`, `STOP`.

Sản phẩm: demo terminal RPi gửi lệnh, STM32 trả `OK`.

### Giai Đoạn 2: Thị Giác Máy Tính

- Cố định camera và đèn.
- Chụp ảnh từng mặt.
- Xác định 9 ô sticker bằng grid hoặc ArUco/reference frame.
- Chuyển RGB sang HSV/LAB.
- Calibration màu từ 6 center stickers.
- Xuất cube string và ảnh debug có overlay.

Sản phẩm: quét 6 mặt và tạo cube string hợp lệ.

### Giai Đoạn 3: Solver Và Motion Planner

- Tích hợp solver Kociemba.
- Map move cube `U D L R F B` sang action robot.
- Thêm action cost để chọn hướng giải/motion ngắn hơn.
- Mô phỏng action list trên terminal.

Sản phẩm: từ cube string -> solution -> robot actions.

### Giai Đoạn 4: Điều Khiển Servo

- Calibration từng servo: home, grip, release, rotate +90, rotate -90.
- Tạo profile tốc độ có delay an toàn.
- Test từng action: grip, release, rotate face, reorient cube.
- Thêm retry khi STM32 NACK hoặc timeout.

Sản phẩm: robot thực thi chuỗi action ngắn, không làm rơi cube.

### Giai Đoạn 5: Chức Năng Luyện Tập

- Sinh scramble theo mức độ.
- Tạo mode hiển thị hướng dẫn giải từng bước.
- Thêm mô tả thân thiện cho người mới học Rubik.
- Log đề bài và lời giải để dùng trong báo cáo/demo.

Sản phẩm: người chơi có thể lấy đề trộn Rubik và xem hướng dẫn giải từng bước.

### Giai Đoạn 6: Full System

- Quét cube thật.
- Giải cube với robot.
- Tạo đề bài, trộn cube, sau đó robot/người chơi có thể giải theo solution.
- Đo thời gian, tỉ lệ thành công, số bước, số action.
- Tinh chỉnh ánh sáng, threshold, servo timing.

Sản phẩm: video demo và số liệu đánh giá.

## 8. Kế Hoạch 8 Tuần Gợi Ý

| Tuần | Mục Tiêu | Đầu Ra |
|---|---|---|
| 1 | Kiến trúc, repo, giao tiếp cơ bản | README, UART protocol, demo CLI |
| 2 | Firmware PWM/servo | Điều khiển từng servo |
| 3 | Camera capture và calibration màu | Ảnh debug 6 mặt |
| 4 | Cube state validation và solver | Solution trong terminal |
| 5 | Motion planner | Action list và cost |
| 6 | Sinh scramble và hướng dẫn từng bước | Chế độ luyện tập cho người chơi |
| 7 | Lắp ráp cơ khí, calibration | Bảng góc servo |
| 8 | Tối ưu, báo cáo, video | Demo và report |

## 9. Rủi Ro Và Cách Giảm

- Ánh sáng thay đổi: dùng đèn cố định, chụp màu center mỗi lần quét.
- Servo không đủ moment: dùng servo kim loại, nguồn riêng, giảm ma sát cơ khí.
- Rubik bị kẹt: dùng cube speed cube, giảm tốc, căn chỉnh kẹp.
- Solver nhận state sai: log ảnh + overlay + histogram để debug.
- Giao tiếp mất gói: có ACK/NACK, sequence id, timeout, retry.

## 10. Tiêu Chí Đánh Giá

- Tỉ lệ nhận diện màu đúng trên tập ảnh test.
- Tỉ lệ cube state hợp lệ sau khi scan.
- Thời gian trung bình từ scan đến solution.
- Số move solver và số action robot.
- Số lượng đề bài tạo được theo từng mức độ.
- Độ đúng của lời giải hiển thị cho người chơi.
- Tỉ lệ giải thành công trong 10 lần thử.
- Thời gian giải trung bình.
