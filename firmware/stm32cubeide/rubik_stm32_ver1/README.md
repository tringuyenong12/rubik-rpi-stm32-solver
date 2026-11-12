# Firmware STM32F411 với PCA9685

Project được tích hợp từ nhánh `stm32_firmware`, commit `704df0a`, vào cấu trúc `firmware/stm32cubeide/` của `main`.

## Mở và build

1. Mở STM32CubeIDE, chọn `File > Import > General > Existing Projects into Workspace`.
2. Chọn thư mục chứa file README này, rồi import project `rubik_stm32_ver1`.
3. Chọn cấu hình `Debug` hoặc `Release`, rồi Build Project.
4. Flash qua ST-Link sau khi kiểm tra wiring và calibration servo.

Project có sẵn `Core/`, `Drivers/`, `Hardware/`, `Testing/`, linker scripts và `rubik_stm32_ver1.ioc`. CubeIDE tạo thư mục build khi biên dịch. Các source entry trong `.cproject` trỏ vào project này.

## Phần cứng

- MCU STM32F411CEUx, clock HSI 16 MHz.
- USART1, 115200 baud, 8N1, TX PA9 và RX PA10.
- I2C1, 400 kHz, SCL PB6 và SDA PB7, điều khiển PCA9685 ở 50 Hz.
- 8 servo, 4 kênh xoay và 4 kênh trượt. Mapping và calibration nằm trong `Hardware/Servo_Control/Servo_Control.c`.
- Khi khởi động, `main.c` đưa servo và cơ cấu kẹp về vị trí ban đầu trước vòng lặp xử lý lệnh.

## Lệnh UART hiện tại

Mỗi lệnh kết thúc bằng LF hoặc CRLF.

```text
#1 TEST_RUBIK MOVE R
#2 TEST_RUBIK MOVE R_
#3 TEST_RUBIK MOVE U
```

Các tham số được nhận gồm `L R U D F B L_ R_ U_ D_ F_ B_`. Mỗi lệnh có đúng ID, nhóm, hành động và tham số mặt. Bộ đệm nhận có 64 byte và giữ một lệnh chờ xử lý. Lệnh đến trong lúc bận có thể bị bỏ qua.

Giao thức này khác với giao thức `RUBIK` có `TURN`, `duration_ms` và ACK được mô tả trong [UART_PROTOCOL.md](../../../docs/UART_PROTOCOL.md). Phía Raspberry Pi hiện chờ ACK, vì vậy tích hợp chạy tự động end-to-end cần đồng bộ parser và phản hồi UART. `Hardware/UART_Handle/README.md` từ nhánh nguồn mô tả phiên bản parser cũ. Định dạng ở trên được đối chiếu với `UART_Handle.c` hiện tại.

## Kiểm tra

Lệnh chạy bộ test được chuyển từ nhánh nguồn

```powershell
python tests/run_tests.py
```

Bộ test nguồn hiện lệch với implementation. Runner thiếu include path `Core/Inc`, test UART gọi các API cũ như `UART_Handle_Process`, và test motion gọi các hàm tên cũ như `Left`. Cần cập nhật bộ test trước khi dùng kết quả để xác nhận firmware. Kiểm tra cú pháp riêng `UART_Handle.c` bằng GCC đã đạt sau khi bổ sung include `<stdio.h>` cho `sscanf`.

Build và flash bằng STM32CubeIDE cùng kiểm tra cơ cấu thật vẫn cần thực hiện trên máy có toolchain và phần cứng tương ứng.
