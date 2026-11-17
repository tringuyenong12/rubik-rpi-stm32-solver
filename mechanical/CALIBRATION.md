# Calibration Cơ Khí Và Servo

## Bảng Servo

Cập nhật bảng này sau khi lắp phần cứng. Theo bản vẽ CAD hiện tại, nên tách actuator thành cụm trượt, đầu tác động và cụm trung tâm thay vì chỉ đặt tên servo 0-5.

| Channel | Chức Năng | Home us | Min us | Max us | Ghi Chú |
|---|---|---:|---:|---:|---|
| 0 | carriage_nw hoặc tool_nw | 1500 | 1000 | 2000 | TBD |
| 1 | carriage_ne hoặc tool_ne | 1500 | 1000 | 2000 | TBD |
| 2 | carriage_sw hoặc tool_sw | 1500 | 1000 | 2000 | TBD |
| 3 | carriage_se hoặc tool_se | 1500 | 1000 | 2000 | TBD |
| 4 | center_lift | 1500 | 1000 | 2000 | optional/TBD |
| 5 | center_rotate | 1500 | 1000 | 2000 | optional/TBD |

Xem thêm [docs/ACTUATOR_MAPPING.md](../docs/ACTUATOR_MAPPING.md).

## Quy Trình Calibration

1. Tháo Rubik ra khỏi robot.
2. Gửi `SERVO <channel> 1500 300`.
3. Tìm giới hạn cơ khí an toàn bằng bước nhỏ 20-50 us.
4. Ghi lại `min`, `home`, `max`.
5. Lắp Rubik vào và thử grip/release với tốc độ chậm.
6. Test quay 90 độ, sau đó 180 độ.
7. Ghi lại thời gian tối thiểu không trượt cube.

## Calibration Cho 4 Cụm Trượt Chéo

1. Tháo Rubik ra khỏi bàn máy.
2. Home từng cụm trượt, ghi lại vị trí an toàn.
3. Cho cụm trượt tiến vào chậm, dừng trước khi đầu tác động chạm vào cube.
4. Lắp Rubik vào, test `approach` với tốc độ chậm.
5. Đánh dấu 3 vị trí:
   - `home`: lùi hết về an toàn.
   - `approach`: gần cube nhưng chưa tạo lực lớn.
   - `engaged`: đủ giữ/xoay mặt cube.
6. Lặp lại cho `carriage_nw`, `carriage_ne`, `carriage_sw`, `carriage_se`.

Nếu có limit switch, mỗi cụm trượt phải home thành công trước khi cho phép chạy solver.

## Lưu Ý Nguồn

Không cấp servo trực tiếp từ chân 5V của Raspberry Pi. Servo cần nguồn riêng, dòng đủ lớn. GND của nguồn servo, STM32 và Raspberry Pi phải nối chung.
