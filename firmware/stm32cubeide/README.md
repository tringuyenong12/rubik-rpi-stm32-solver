# Firmware STM32CubeIDE

Project chính nằm trực tiếp trong thư mục này, dùng STM32F411CEUx + PCA9685.

```text
stm32cubeide/
  .project, .cproject         Project STM32CubeIDE
  rubik_stm32_ver1.ioc        Cấu hình CubeMX
  Core/                      Khởi tạo MCU, main và ngắt HAL
  App/rubik_protocol.*       Frame UART, tag và kiểm tra tham số
  App/UART_Handle/           Xử lý lệnh và phản hồi ACK/DONE/NACK
  Hardware/PCA9685/          Driver PWM qua I2C
  Hardware/Servo_Control/    Mapping kênh và calibration servo
  Hardware/Rubik_Control/    Chuỗi kẹp và xoay Rubik
  Drivers/                   STM32 HAL và CMSIS
  Testing/                   File thử nghiệm của project nguồn
  tests/                     Kiểm thử trên máy bằng GCC
  examples/timer_pwm/        Bản mẫu timer PWM cũ
```

## Mở project

1. Trong STM32CubeIDE, chọn `File > Import > General > Existing Projects into Workspace`.
2. Chọn `firmware/stm32cubeide`, import project `rubik_stm32_ver1`.
3. Build cấu hình Debug hoặc Release.
4. Flash qua ST-Link sau khi kiểm tra wiring và calibration.

Nếu đã import project ở đường dẫn cũ, gỡ project khỏi workspace bằng tùy chọn giữ file trên đĩa rồi import lại đường dẫn ở trên. Đặt workspace CubeIDE bên ngoài thư mục source.

CubeMX quản lý Core, Drivers và file .ioc. Code ứng dụng nằm trong App, driver và chuỗi cơ khí nằm trong Hardware. Đặt include và lời gọi ứng dụng trong các block USER CODE của main.c. Cả Debug và Release biên dịch App, Core, Drivers, Hardware và Testing.

## Phần cứng

- STM32F411CEUx, HSI 16 MHz.
- USART1, 115200 baud, 8N1, TX PA9 và RX PA10.
- I2C1, 400 kHz, SCL PB6 và SDA PB7.
- PCA9685 chạy PWM 50 Hz, 8 servo gồm 4 kênh xoay và 4 kênh trượt.
- Mapping và calibration nằm trong Hardware/Servo_Control/Servo_Control.c.

Core/Src/main.c khởi tạo PCA9685 và servo, đưa cơ cấu về vị trí ban đầu rồi xử lý UART trong vòng lặp chính. Ngắt HAL chuyển byte nhận cho module UART. Chờ hoàn tất khởi động trước khi kết nối từ Pi.

## Giao tiếp

Xem [hướng dẫn UART](App/UART_Handle/README.md) và [giao thức Raspberry Pi](../../docs/UART_PROTOCOL.md).

```text
#1 RUBIK PING
#2 RUBIK TURN R 1 450
#3 RUBIK MOVE R_ -1 450
```

UART trả ACK/DONE/NACK đúng tag và hỗ trợ lệnh TEST_RUBIK MOVE cũ. U đảo và các lệnh D trả NACK vì chuỗi chuyển động nguồn còn lỗi hoặc thiếu. STOP khóa các lệnh chuyển động cho đến HOME và được xử lý sau khi chuỗi đang chạy kết thúc.

Nhóm CALIB hỗ trợ SERVO để thử xung PWM, SET để chỉnh góc các vị trí HOME/CLAMP và TEST để chạy thử vị trí đã chỉnh. Calibration được dùng ngay và lưu trong RAM. Ví dụ `#c1 CALIB SET 0 HOME 92.5` rồi `#c2 CALIB TEST 0 HOME 500`. Phần xử lý nằm trong hàm process_calibration của App/UART_Handle/UART_Handle.c.

## Kiểm thử

Từ thư mục này, chạy bằng Python và GCC

```powershell
python tests/run_tests.py --uart-only
python tests/run_tests.py
```

Test UART kiểm tra frame, tham số, phản hồi, dispatch, STOP/HOME và phục hồi RX. Test chuyển động toàn bộ hiện còn thất bại ở chuỗi U đảo. Rubik_Down_ToFront đang trống và chuỗi D thuận cần xác nhận lại. UART đã từ chối các chuỗi này.

Build/flash bằng toolchain STM32 và kiểm tra cơ cấu thật vẫn cần xác nhận. Bản mẫu TIM PWM cũ cùng các thay đổi có sẵn trên máy nằm tại [examples/timer_pwm](examples/timer_pwm/README.md).

## Bản mẫu timer PWM

Driver ServoController và snippet dùng timer PWM nằm riêng tại `examples/timer_pwm/`.
Đọc [hướng dẫn servo](App/SERVO_CONTROLLER_GUIDE.md) để cấu hình profile thực tế
trước khi bật PWM cho bản mẫu này. Đây là driver khác với PCA9685 của project chính.
Chạy test driver và biên dịch kiểm tra snippet từ thư mục gốc:
`python firmware/tests/run_tests.py`.
