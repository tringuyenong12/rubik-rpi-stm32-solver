# UART của firmware PCA9685

USART1 chạy 115200 baud, 8N1, TX PA9 và RX PA10. Frame ASCII kết thúc bằng LF hoặc CRLF, tối đa 95 ký tự trước ký tự kết thúc dòng.

```text
#abc123 RUBIK PING
#move1 RUBIK TURN R 1 450
#move2 RUBIK MOVE R_ -1 450
#move3 RUBIK MOVE R 2 900
#calib1 RUBIK SERVO 0 1500 300
#stop1 RUBIK STOP
#home1 RUBIK HOME
```

Tag dài 1–32 ký tự ASCII, gồm chữ, số, dấu gạch dưới hoặc gạch ngang. Phản hồi luôn có cùng tag.

```text
#move1 ACK
#move1 DONE
```

PING và STOP chỉ trả ACK. HOME, SERVO, MOVE và TURN trả ACK trước khi gọi phần cứng, rồi DONE khi hàm xử lý hoàn tất. Frame sai trả NACK cùng mã lỗi. Lệnh thử cũ như `#1 TEST_RUBIK MOVE R_` vẫn được hỗ trợ và nhận cùng kiểu phản hồi.

## Các lệnh

| Lệnh | Tham số | Xử lý |
| --- | --- | --- |
| PING | Không | Kiểm tra kết nối |
| HOME | Không | Gọi Rubik_Hold_Start_Position và xóa trạng thái STOP |
| STOP | Không | Khóa lệnh MOVE, TURN và SERVO cho đến HOME |
| MOVE, TURN | face, hoặc face turns duration_ms | Gọi chuỗi chuyển động trong Rubik_Control |
| SERVO | channel pulse_us duration_ms | Gửi PWM trực tiếp đến PCA9685 |
| ACTUATOR, CLAMP, SCAN_POSE | Theo giao thức mở rộng | NACK UNSUPPORTED |
| Nhóm khác RUBIK/CALIB | Theo nhóm | NACK UNSUPPORTED |

MOVE/TURN hỗ trợ mặt L, R, F, B theo hai chiều và U thuận. U đảo, D và D đảo trả `NACK UNSUPPORTED motion_incomplete` do các chuỗi nguồn còn lỗi hoặc thiếu.

Turns nhận 1, -1 hoặc 2. Dấu `_` sau mặt chọn chiều đảo, khi kèm turns thì turns phải là -1. Turns 2 gọi chuỗi thuận hai lần. Dạng ngắn `MOVE R` mặc định turns=1 và duration_ms=450. Khi thêm turns phải cung cấp cả duration_ms.

Duration nhận số nguyên 0–60000 ms. Với MOVE/TURN, đây là thời gian tối thiểu của cả lệnh. Các bước servo vẫn dùng thời gian trong Servo_Control. Với SERVO, firmware chờ duration sau khi gửi PWM. Kênh PCA9685 nhận 0–15, pulse nhận 500–2500 microsecond tại 50 Hz. DONE xác nhận hàm điều khiển đã chạy xong, driver hiện chưa phản hồi lỗi I2C hoặc vị trí servo thật.

## Nhóm CALIB

Các lệnh trong nhóm CALIB trả ACK rồi DONE khi thành công. Lệnh sai trả NACK cùng tag.

```text
#c1 CALIB SERVO 0 1500 300
#c2 CALIB SET 0 HOME 92.5
#c3 CALIB TEST 0 HOME 500
#c4 CALIB SET 4 CLAMP 12
#c5 CALIB TEST 4 CLAMP 500
```

| Lệnh | Tham số | Tác dụng |
| --- | --- | --- |
| CALIB SERVO | channel pulse_us duration_ms | Thử xung trực tiếp, kênh 0–15, xung 500–2500 us |
| CALIB SET | servo_id position angle_deg | Cập nhật góc cuối của một vị trí trong cấu hình RAM |
| CALIB TEST | servo_id position duration_ms | Chạy servo đến vị trí đã chỉnh rồi chờ duration_ms |

SERVO cũng chấp nhận tên thao tác viết thường `servo` để tương thích với ví dụ Python đã có. SET và TEST dùng tên viết hoa. Duration nhận số nguyên 0–60000 ms, angle_deg nhận số thập phân 0–180 độ.

| Servo ID | Vai trò | Các vị trí dùng với SET và TEST |
| --- | --- | --- |
| 0 | Xoay FRONT | HOME, CLOCKWISE, ANTICLOCKWISE |
| 1 | Xoay RIGHT | HOME, CLOCKWISE, ANTICLOCKWISE |
| 2 | Xoay BACK | HOME, CLOCKWISE, ANTICLOCKWISE |
| 3 | Xoay LEFT | HOME, CLOCKWISE, ANTICLOCKWISE |
| 4 | Trượt FRONT | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |
| 5 | Trượt RIGHT | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |
| 6 | Trượt BACK | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |
| 7 | Trượt LEFT | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |

SET và TEST chọn servo theo ID trong mảng `servo[]`. TEST dùng kênh PCA9685 đã được gán tại `servo[id].channel`. SERVO chọn trực tiếp số kênh vật lý.

Ví dụ HOME mặc định là 90 độ. Lệnh SET HOME 92.5 đặt offset HOME thành +2.5 độ. Các lệnh RUBIK sau đó tự dùng giá trị mới vì các hàm Servo_Rotate và Servo_Move đọc cùng cấu hình. SET chỉ cập nhật cấu hình, lệnh TEST áp dụng vị trí ra servo.

Giá trị calibration hiện được giữ trong RAM và trở về cấu hình trong Servo_Control.c sau khi reset hoặc mất điện. Để giữ kết quả lâu dài, điền các offset đã tìm được vào phần khởi tạo mảng servo[] trong file đó rồi build/flash.

STOP khóa CALIB TEST và CALIB SERVO cho đến RUBIK HOME. CALIB SET vẫn cập nhật cấu hình khi đang STOP. TEST điều khiển riêng servo được chọn, nên cần kiểm tra trạng thái kẹp của cơ cấu trước khi chạy.

Luồng code của nhóm CALIB đi qua parse_line trong App/rubik_protocol.c, rồi process_calibration trong UART_Handle.c. SET gọi Servo_SetRotateCalibration hoặc Servo_SetMoveCalibration, TEST gọi Servo_Rotate hoặc Servo_Move.

## Tích hợp

- `App/rubik_protocol.*` quản lý frame, tag, kiểm tra tham số và phản hồi.
- `UART_Command_Init(&huart1)` khởi tạo nhận byte bằng ngắt.
- `UART_Command_RxCallback(huart)` được gọi từ HAL_UART_RxCpltCallback.
- `UART_Command_ErrorCallback(huart)` được gọi từ HAL_UART_ErrorCallback để bỏ phần frame hỏng và khởi động lại nhận.
- `UART_Command_Process()` chạy trong vòng lặp chính để thực hiện chuyển động.

Ngắt chỉ thu byte. Vòng lặp chính sao chép frame trong vùng ngắt được khóa ngắn rồi xử lý. Có một vị trí cho frame đang chờ. Mỗi phía gửi nên chờ phản hồi kết thúc trước lệnh tiếp theo. Frame quá dài hoặc chứa ký tự điều khiển bị từ chối toàn bộ. Phần đuôi frame bị mất do bận cũng được bỏ đến hết dòng.

STOP được thực hiện khi vòng lặp chính xử lý đến lệnh đó. Các hàm chuyển động hiện dùng HAL_Delay nên STOP chờ chuỗi đang chạy kết thúc. Khi STOP được xử lý, PWM tiếp tục giữ vị trí hiện tại.

Trên Pi, SerialLink chờ ACK theo timeout_s, mặc định 2 giây, và chờ DONE theo motion_timeout_s, mặc định 65 giây. Tham số timeout_s lớn hơn vẫn được tôn trọng. Chờ cơ cấu hoàn tất khởi động trước khi kết nối.

Chạy test bằng `python tests/run_tests.py --uart-only` từ thư mục project. Build và flash bằng STM32CubeIDE trước khi kiểm tra trên phần cứng.
