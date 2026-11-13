# Cấu Hình STM32CubeIDE

Project chính nằm tại `firmware/stm32cubeide`. Import bằng `File > Import > General > Existing Projects into Workspace`, chọn project `rubik_stm32_ver1`, rồi build Debug hoặc Release.

Cấu hình hiện tại dùng STM32F411CEUx, HSI 16 MHz, USART1 PA9/PA10 115200 baud và I2C1 PB6/PB7 400 kHz nối PCA9685. Logic UART nằm trong App, driver và chuyển động nằm trong Hardware. Chi tiết trong [README firmware](../firmware/stm32cubeide/README.md).

## Bản mẫu timer PWM

Phần bên dưới hướng dẫn tạo project mới theo bản mẫu tại `firmware/stm32cubeide/examples/timer_pwm`. Bản mẫu này dùng timer PWM và giao thức RUBIK có ACK/DONE.

Tài liệu này thay cho workflow PlatformIO. Mục tiêu là để STM32CubeIDE sinh code khởi tạo peripheral, còn logic robot nằm trong `firmware/stm32cubeide/examples/timer_pwm/App`.

## 1. Tạo Project

1. Mở STM32CubeIDE.
2. `File -> New -> STM32 Project`.
3. Chọn MCU/board đúng với phần cứng của bạn.
4. Đặt tên project: `RubikServoController`.
5. Chọn `C` project.

Nếu dùng Blue Pill phổ biến, MCU thường là `STM32F103C8Tx`.

## 2. Clock

Với STM32F103C8Tx:

- Chọn HSE nếu board có thạch anh 8 MHz.
- Cấu hình SYSCLK 72 MHz.
- APB1 prescaler `/2`.
- APB2 prescaler `/1`.

Nếu board khác, chỉ cần đảm bảo timer PWM có clock ổn định và UART đặt đúng 115200 baud.

## 3. UART

Bật `USART1` hoặc `USART2`:

- Mode: Asynchronous
- Baudrate: `115200`
- Word Length: 8 Bits
- Parity: None
- Stop Bits: 1
- NVIC interrupt: Enable

Nếu dùng `USART1` trên STM32F103 Blue Pill:

- TX: PA9
- RX: PA10

Nối với Raspberry Pi:

- STM32 TX -> RPi RX
- STM32 RX -> RPi TX
- GND chung

Lưu ý mức logic đều là 3.3V, phù hợp với Raspberry Pi.

## 4. Timer PWM Cho Servo

Servo RC cần PWM 50 Hz, chu kỳ 20 ms. Pulse thường dùng:

- 1000 us: một đầu
- 1500 us: home/center
- 2000 us: đầu còn lại

Với STM32F103 clock timer 72 MHz, cấu hình TIM2:

- Prescaler: `72 - 1`
- Counter Period: `20000 - 1`
- PWM Generation CH1: Enable
- PWM Generation CH2: Enable
- PWM Generation CH3: Enable
- PWM Generation CH4: Enable
- Pulse ban đầu: `1500`

Khi đó timer tick là 1 us, nên compare value bằng trực tiếp `pulse_us`.

Pin mặc định TIM2 trên STM32F103:

- CH1: PA0
- CH2: PA1
- CH3: PA2
- CH4: PA3

## 4.1. Lưu Ý Theo Bản Vẽ Cơ Khí

Bản vẽ hiện tại có 4 cụm trượt chéo quanh cube và một cụm trung tâm dưới mặt bàn. Vì vậy phần cứng có thể cần nhiều hơn 4 kênh điều khiển:

- 4 kênh cho carriage/rack-pinion nếu dùng servo liên tục hoặc stepper/DC driver.
- 4 kênh cho tool/đầu kẹp/đầu xoay nếu mỗi cụm có một đầu tác động riêng.
- 1-2 kênh cho `center_lift` và `center_rotate`.

Với STM32F103, có thể dùng thêm TIM3/TIM4 hoặc driver PWM ngoài như PCA9685 nếu số servo vượt quá timer channel có sẵn.

Firmware trong `firmware/stm32cubeide/examples/timer_pwm/App` hiện là scaffold an toàn:

- `SERVO` để test từng kênh PWM.
- `MOVE`, `TURN`, `SCAN_POSE` trả lỗi chưa hỗ trợ cho đến khi có sequence cơ khí.
- Mapping actuator thật sẽ được điền sau khi chốt motor và cảm biến cho từng cụm.

Phải gọi `ServoController_ConfigProfile()` với số đo thực tế trước `Start()`.
Không có profile thì PWM không bật. Cấu hình nhiều timer và ba mốc góc theo
[hướng dẫn thư viện](../firmware/stm32cubeide/App/SERVO_CONTROLLER_GUIDE.md).

## 5. Thêm Code App

Copy thư mục:

```text
firmware/stm32cubeide/examples/timer_pwm/App
```

vào project CubeIDE.

Trong project properties:

- `C/C++ General -> Paths and Symbols -> Includes`
- thêm đường dẫn `App`

Hoặc trong CubeIDE, click phải project và refresh để IDE tự nhận source mới.

## 6. Chèn Code Vào `main.c`

Mở:

```text
Core/Src/main.c
```

Chèn các đoạn từ:

```text
firmware/stm32cubeide/examples/timer_pwm/Core_Src_main_user_snippet.c
```

vào đúng các block:

```c
/* USER CODE BEGIN Includes */
/* USER CODE END Includes */

/* USER CODE BEGIN PV */
/* USER CODE END PV */

/* USER CODE BEGIN 2 */
/* USER CODE END 2 */

/* USER CODE BEGIN WHILE */
/* USER CODE END WHILE */

/* USER CODE BEGIN 4 */
/* USER CODE END 4 */
```

Không viết code ngoài các block `USER CODE`, vì CubeMX có thể ghi đè khi regenerate.

## 7. Test Nhanh

Sau khi flash, mở Serial Monitor 115200 baud và gửi:

```text
#1 RUBIK PING
```

STM32 phải trả:

```text
#1 ACK
```

Sau khi đã cấu hình profile cho kênh 0, thử pulse nằm trong giới hạn đã đo
(các số dưới đây chỉ minh họa):

```text
#2 RUBIK SERVO 0 1500 300
#3 RUBIK SERVO 0 1600 300
#4 RUBIK SERVO 0 1400 300
```

Nếu servo đi ngược/quá góc, dừng ngay và cập nhật giới hạn trong `servo_controller.c`.
