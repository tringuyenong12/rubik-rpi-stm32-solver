# Bản UART để build và nạp

Project dùng với VS Code: `firmware/vscode-f411/rubik_stm32_ver1`.
Bản STM32CubeIDE gốc: `firmware/stm32cubeide`. Phần sửa UART đã được đồng bộ vào cả hai bản.

## Kết quả kiểm tra

- Test UART trên máy tính chạy qua cho cả hai project: giải mã, ACK/DONE/NACK,
  giới hạn tham số, CALIB, STOP/HOME, frame dài, byte lỗi, nhận khi bận và phục hồi lỗi.
- 13 test SerialLink phía Raspberry Pi chạy qua.
- Build ARM Debug thành công, sinh `.elf`, `.hex` và `.bin` trong
  `firmware/vscode-f411/rubik_stm32_ver1/build/Debug/`.
- Đã sửa lỗi callback nhận khởi động lại RX quá sớm, xóa ErrorCode trước khi
  HAL xử lý xong. Chỉ khởi động lại trong callback lỗi và xóa cờ lỗi phần cứng.
- Chưa xác nhận truyền UART trên STM32 thật: lúc kiểm tra, CubeProgrammer không
  tìm thấy ST-Link và máy chỉ có COM5/COM6 Bluetooth, chưa có cổng USB–TTL.

Test chuyển động đầy đủ vẫn thất bại ở chuỗi U đảo. Chuỗi D cũng chưa hoàn chỉnh.
UART tiếp tục trả `NACK UNSUPPORTED motion_incomplete` cho U đảo, D và D đảo.
Không dùng kết quả test UART để kết luận toàn bộ cơ cấu Rubik đã hoạt động đúng.

## Nạp và kiểm tra

1. Cắm ST-Link vào máy, nối SWD và cấp nguồn STM32 như cấu hình đã nạp thành công.
2. Mở folder `firmware/vscode-f411/rubik_stm32_ver1` trong VS Code.
3. Chọn Run and Debug → `STM32: Flash and Debug (ST-Link V2)` → F5.
4. Chờ `Download verified successfully`. Khi debugger dừng tại main, nhấn F5
   để chạy tiếp. Chờ khoảng 10 giây để firmware hoàn tất khởi động.

Firmware hiện tự đưa servo về vị trí khởi động rồi kẹp khi khởi động.
Nếu đã nối nguồn servo, cơ cấu sẽ chuyển động lúc này.

Nối USB–TTL dùng tín hiệu UART 3,3 V:

| USB–TTL | STM32 |
| --- | --- |
| TXD | A10 / PA10 |
| RXD | A9 / PA9 |
| GND | GND |

Để trống VCC của USB–TTL khi STM32 đã được cấp nguồn bằng ST-Link.
Cắm đầu USB của USB–TTL vào laptop. Chọn đúng cổng COM USB–TTL; COM Bluetooth
không nối với STM32. Nếu thiết bị USB–TTL chưa có COM, cần xử lý driver trước.

Serial Monitor: **115200, 8N1, không flow control, line ending LF**.
Gửi từng lệnh và chờ phản hồi:

```text
#1 RUBIK PING
```

Kết quả mong đợi:

```text
#1 ACK
```

Để test tự động, đóng Serial Monitor để nhả cổng, mở terminal tại thư mục gốc repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test-uart.ps1 -Port COM7
```

Thay COM7 bằng cổng USB–TTL thực tế. Script dùng thư viện có sẵn của Windows,
không cần cài Python/pyserial. Script gửi 100 PING, thử CR/LF/CRLF, frame chia nhỏ,
frame sai, frame quá dài và phục hồi. Chỉ khi nhận đủ 109 phản hồi đúng mới in PASS.
Script không gửi lệnh chuyển động và không ghi calibration.

## Đọc code ở đâu

| File trong project | Vai trò |
| --- | --- |
| `Core/Src/main.c` | Khởi tạo, callback HAL, vòng lặp xử lý |
| `App/rubik_protocol.c` | Thu frame, giải mã, kiểm tra tham số, gửi phản hồi |
| `App/UART_Handle/UART_Handle.c` | Chọn nhóm RUBIK/CALIB và gọi hàm xử lý |
| `Hardware/Servo_Control/Servo_Control.c` | Góc và offset calibration của từng servo |

Các lệnh CALIB hiện có:

```text
#c1 CALIB SET 0 HOME 92.5
#c2 CALIB TEST 0 HOME 500
```

SET chỉ cập nhật góc trong RAM; TEST mới điều khiển servo. Mỗi lệnh thành công
trả ACK rồi DONE. Giá trị SET mất khi reset. Hướng dẫn đầy đủ và danh sách servo
nằm trong `App/UART_Handle/README.md`.

TEST dùng đúng các enum vị trí của Servo_Control, gọi Servo_Rotate cho ID 0–3,
Servo_Move cho ID 4–7 rồi gọi waitUntilServosDone. Với driver hiện tại, TEST
chờ ít nhất 1.000 ms trước DONE, hoặc lâu hơn nếu duration_ms lớn hơn 1.000.
SET tính offset = góc yêu cầu − góc gốc; gửi SET nhiều lần không cộng dồn offset.
CALIB SERVO vẫn là lệnh xung thô theo kênh vật lý, không sửa offset.

Mỗi lần chỉ gửi một lệnh, chờ ACK với PING/STOP hoặc DONE/NACK với lệnh khác
trước khi gửi tiếp. STOP được xử lý sau khi chuỗi chuyển động đang chạy kết thúc;
không phải dừng khẩn cấp. DONE chỉ xác nhận phần mềm chạy xong, chưa xác nhận
vị trí thật của servo hay việc ghi I2C thành công.

## Chạy lại test phần mềm

Từ thư mục gốc repo, với Python và GCC đã có trong PATH:

```powershell
python firmware/stm32cubeide/tests/run_tests.py --uart-only
python firmware/stm32cubeide/tests/run_tests.py --uart-only --project firmware/vscode-f411/rubik_stm32_ver1
$env:PYTHONPATH = (Resolve-Path rpi).Path
python -m unittest discover -s rpi/tests -p test_serial_link.py
```
