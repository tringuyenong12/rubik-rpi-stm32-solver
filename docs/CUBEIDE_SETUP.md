# Cau Hinh STM32CubeIDE

Tai lieu nay thay cho workflow PlatformIO. Muc tieu la de STM32CubeIDE sinh code khoi tao peripheral, con logic robot nam trong `firmware/stm32cubeide/App`.

## 1. Tao Project

1. Mo STM32CubeIDE.
2. `File -> New -> STM32 Project`.
3. Chon MCU/board dung voi phan cung cua ban.
4. Dat ten project: `RubikServoController`.
5. Chon `C` project.

Neu dung Blue Pill pho bien, MCU thuong la `STM32F103C8Tx`.

## 2. Clock

Voi STM32F103C8Tx:

- Chon HSE neu board co thach anh 8 MHz.
- Cau hinh SYSCLK 72 MHz.
- APB1 prescaler `/2`.
- APB2 prescaler `/1`.

Neu board khac, chi can dam bao timer PWM co clock on dinh va UART dat dung 115200 baud.

## 3. UART

Bat `USART1` hoac `USART2`:

- Mode: Asynchronous
- Baudrate: `115200`
- Word Length: 8 Bits
- Parity: None
- Stop Bits: 1
- NVIC interrupt: Enable

Neu dung `USART1` tren STM32F103 Blue Pill:

- TX: PA9
- RX: PA10

Noi voi Raspberry Pi:

- STM32 TX -> RPi RX
- STM32 RX -> RPi TX
- GND chung

Luu y muc logic deu la 3.3V, phu hop voi Raspberry Pi.

## 4. Timer PWM Cho Servo

Servo RC can PWM 50 Hz, chu ky 20 ms. Pulse thuong dung:

- 1000 us: mot dau
- 1500 us: home/center
- 2000 us: dau con lai

Voi STM32F103 clock timer 72 MHz, cau hinh TIM2:

- Prescaler: `72 - 1`
- Counter Period: `20000 - 1`
- PWM Generation CH1: Enable
- PWM Generation CH2: Enable
- PWM Generation CH3: Enable
- PWM Generation CH4: Enable
- Pulse ban dau: `1500`

Khi do timer tick la 1 us, nen compare value bang truc tiep `pulse_us`.

Pin mac dinh TIM2 tren STM32F103:

- CH1: PA0
- CH2: PA1
- CH3: PA2
- CH4: PA3

## 4.1. Luu Y Theo Ban Ve Co Khi

Ban ve hien tai co 4 cum truot cheo quanh cube va mot cum trung tam duoi mat ban. Vi vay phan cung co the can nhieu hon 4 kenh dieu khien:

- 4 kenh cho carriage/rack-pinion neu dung servo lien tuc hoac stepper/DC driver.
- 4 kenh cho tool/dau kep/dau xoay neu moi cum co mot dau tac dong rieng.
- 1-2 kenh cho `center_lift` va `center_rotate`.

Voi STM32F103, co the dung them TIM3/TIM4 hoac driver PWM ngoai nhu PCA9685 neu so servo vuot qua timer channel co san.

Firmware trong `firmware/stm32cubeide/App` hien la scaffold an toan:

- `SERVO` de test tung kenh PWM.
- `MOVE` de test pipeline UART.
- Mapping actuator that se duoc dien sau khi chot motor va cam bien cho tung cum.

## 5. Them Code App

Copy thu muc:

```text
firmware/stm32cubeide/App
```

vao project CubeIDE.

Trong project properties:

- `C/C++ General -> Paths and Symbols -> Includes`
- them duong dan `App`

Hoac trong CubeIDE, click phai project va refresh de IDE tu nhan source moi.

## 6. Chen Code Vao `main.c`

Mo:

```text
Core/Src/main.c
```

Chen cac doan tu:

```text
firmware/stm32cubeide/Core_Src_main_user_snippet.c
```

vao dung cac block:

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

Khong viet code ngoai cac block `USER CODE`, vi CubeMX co the ghi de khi regenerate.

## 7. Test Nhanh

Sau khi flash, mo Serial Monitor 115200 baud va gui:

```text
PING
```

STM32 phai tra:

```text
OK PONG
```

Thu calibration servo:

```text
SERVO 0 1500 300
SERVO 0 1600 300
SERVO 0 1400 300
```

Neu servo di nguoc/qua goc, dung ngay va cap nhat gioi han trong `servo_controller.c`.

