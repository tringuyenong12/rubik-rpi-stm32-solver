# Raspberry Pi 4 ↔ STM32F411CEU6: UART nhị phân ổn định

Tài liệu này dùng cho cơ cấu 8 servo theo mapping của dự án:

| Servo | Vai trò |
|---:|---|
| 0 / 1 | ngàm / thanh trượt mặt F |
| 2 / 3 | ngàm / thanh trượt mặt B |
| 4 / 5 | ngàm / thanh trượt mặt L |
| 6 / 7 | ngàm / thanh trượt mặt R |

## Nối dây và CubeMX

Trên STM32F411CEU6, bật `USART2` ở chế độ Asynchronous, `115200`, 8 data bits,
no parity, 1 stop bit, và bật interrupt USART2 trong NVIC.

| Raspberry Pi 4 | STM32F411CEU6 | Ghi chú |
|---|---|---|
| GPIO14 / TXD (pin 8) | PA3 / USART2_RX | nối chéo TX → RX |
| GPIO15 / RXD (pin 10) | PA2 / USART2_TX | nối chéo RX → TX |
| GND (pin 6) | GND | bắt buộc dùng mass chung |

Cả hai đầu UART đều là 3.3 V. Không cấp nguồn servo từ Raspberry Pi hoặc từ
nguồn 3.3 V của STM32; dùng nguồn 5–6 V riêng đủ dòng cho servo và nối GND của
nguồn này vào GND chung. Cài tụ điện gần cụm servo để tránh sụt áp làm reset STM32.

Trên Raspberry Pi, bật UART, tắt serial login shell, và dùng `/dev/serial0`
(symlink ổn định dù UART chính thay đổi):

```text
enable_uart=1
dtoverlay=disable-bt
```

Sau khi sửa `/boot/firmware/config.txt` (hoặc `/boot/config.txt` tùy OS), khởi
động lại Pi. Người chạy chương trình phải có quyền mở serial, ví dụ thuộc nhóm
`dialout`.

## Firmware STM32

1. Copy `firmware/stm32cubeide/App/rubik_motion.[ch]` và
   `rubik_binary_protocol.[ch]` vào thư mục `App/` trong dự án CubeIDE.
2. Thêm `App` vào include path nếu CubeIDE chưa tự nhận.
3. Chèn nội dung trong
   `firmware/stm32cubeide/Core_Src_main_user_snippet.c` vào các vùng `USER CODE`
   tương ứng. Dùng `huart2` như trong snippet.
4. Hàm servo hiện có phải được công khai với đúng dạng sau và điều khiển đủ 8 kênh:

```c
void servoAngle(int servo_index, int angle_deg);
```

`servo_index` là 0–7 và góc là 0–180. Nếu dùng PCA9685, hàm này chỉ cần đổi độ
sang pulse PWM và ghi vào kênh PCA9685 tương ứng. Giá trị `PULL=0`, `PUSH=60` và
các góc 0/90/180 chỉ là điểm khởi đầu; phải calibration khi không gắn hoặc tháo
khối Rubik trước.

Không đặt `rotate_face`, `rotate_cube`, `HAL_Delay`, hoặc điều khiển servo trong
`HAL_UART_RxCpltCallback`. Callback mới chỉ ghép 4 byte của frame; vòng lặp chính
thực hiện chuyển động.

## Giao thức frame

Pi gửi một lệnh:

```text
A5  SEQ  COMMAND  CRC8(SEQ, COMMAND)
```

STM32 trả về:

```text
5A  SEQ  STATUS   CRC8(SEQ, STATUS)
```

CRC là CRC-8/ATM, polynomial `0x07`, init `0x00`, không reflect, xorout `0x00`.

- `STATUS=06`: ACK, STM32 đã nhận và sẽ chạy lệnh.
- `STATUS=44`: DONE, chuyển động đã hoàn tất; chỉ lúc này Pi gửi bước tiếp theo.
- `STATUS=15`: lỗi frame/lệnh.
- `STATUS=42`: bận.

Nếu ACK hoặc DONE bị mất, Raspberry Pi gửi lại đúng **cùng SEQ**. Firmware ghi
nhớ lệnh hoàn tất gần nhất và chỉ phát lại DONE, không xoay khối lần thứ hai.

| COMMAND | Nước đi |
|---:|---|
| 1, 2, 3 | F, F', F2 |
| 4, 5, 6 | B, B', B2 |
| 7, 8, 9 | L, L', L2 |
| 10, 11, 12 | R, R', R2 |
| 13, 14, 15 | U, U', U2 |
| 16, 17, 18 | D, D', D2 |
| `00` | PING |
| `FE` | HOME: ngàm 90°, thanh trượt PUSH |
| `FF` | FINISH: gọi hook buzzer/LED tùy chọn |

`U`/`D` dùng chuỗi lật khối đúng theo code cơ khí, vì thế timeout của Pi dài hơn
F/B/L/R. Không gửi frame thô một byte `1`–`18`: không có CRC, sequence hay ACK
nên một byte nhiễu có thể làm xoay sai cube.

## Chạy từ Raspberry Pi

Sau khi cài `pyserial` và dependencies trong `rpi/`:

```bash
python -m rubik_robot.main --mode scramble --length 25
python -m rubik_robot.main --mode scramble --length 25 --execute --port /dev/serial0
```

Lệnh đầu chỉ in nước trộn cùng chuỗi 54 ký tự hợp lệ. Lệnh thứ hai in chuỗi đó
**trước**, sau đó gửi từng nước theo ACK/DONE. Để giải một chuỗi quét được:

```bash
python -m rubik_robot.main --mode send --cube '<54_FACELETS>' --port /dev/serial0
```

Tùy chọn `--uart-protocol text` chỉ dành cho firmware ASCII cũ trong repository;
không dùng nó với `rubik_binary_protocol.c`.
