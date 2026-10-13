# UART Protocol RPi <-> STM32

## Cấu Hình Mặc Định

- Baudrate: 115200
- Data bits: 8
- Parity: none
- Stop bits: 1
- Line ending: `\n`
- Encoding: ASCII/UTF-8

## Lệnh

### PING

```text
PING
```

Phản hồi:

```text
OK PONG
```

### HOME

```text
HOME
```

Phản hồi:

```text
OK HOME
DONE HOME
```

### MOVE

```text
MOVE <face> <turns> <duration_ms>
```

Trong đó:

- `face`: `U`, `R`, `F`, `D`, `L`, `B`
- `turns`: `1` là 90 độ thuận, `-1` là 90 độ nghịch, `2` là 180 độ
- `duration_ms`: thời gian servo thực hiện action

Ví dụ:

```text
MOVE R 1 450
MOVE U -1 450
MOVE F 2 700
```

Phản hồi:

```text
OK MOVE
DONE MOVE
```

### SERVO

Dùng cho calibration từng servo.

```text
SERVO <channel> <pulse_us> <duration_ms>
```

Ví dụ:

```text
SERVO 0 1500 300
```

### STOP

```text
STOP
```

Phản hồi:

```text
OK STOP
```

## Lệnh Mở Rộng Theo Bản Vẽ Cơ Khí

Theo bản vẽ CAD hiện tại, robot có 4 cụm trượt chéo và cụm trung tâm. Các lệnh dưới đây phù hợp hơn cho giai đoạn tích hợp cơ khí.

### ACTUATOR

Di chuyển một actuator logic đến target.

```text
ACTUATOR <role> <target> <duration_ms>
```

Ví dụ:

```text
ACTUATOR carriage_nw home 800
ACTUATOR carriage_ne approach 500
ACTUATOR center_lift scan 700
```

Role đề xuất:

- `carriage_nw`
- `carriage_ne`
- `carriage_sw`
- `carriage_se`
- `center_lift`
- `center_rotate`

Target đề xuất:

- `home`
- `approach`
- `engaged`
- `retract`
- `scan`
- `solve`
- `safe`

### CLAMP

Đóng/mở đầu kẹp hoặc đầu tác động.

```text
CLAMP <role> <open|close>
```

Ví dụ:

```text
CLAMP tool_nw close
CLAMP tool_nw open
```

### TURN

Lệnh xoay một mặt Rubik theo abstraction cơ khí. `TURN` nên thay thế `MOVE` khi bắt đầu tích hợp cơ khí thật.

```text
TURN <face> <turns> <duration_ms>
```

Ví dụ:

```text
TURN R 1 450
TURN U -1 450
```

### SCAN_POSE

Đưa cube về tư thế để camera chụp một mặt.

```text
SCAN_POSE <face>
```

Ví dụ:

```text
SCAN_POSE U
SCAN_POSE F
```

## Lỗi

```text
ERR <code> <message>
```

Code đề xuất:

- `BAD_CMD`: sai lệnh.
- `BAD_ARG`: sai tham số.
- `BUSY`: STM32 đang thực thi.
- `LIMIT`: góc servo vượt giới hạn.
- `TIMEOUT`: action quá thời gian an toàn.

## Nâng Cấp Sau

ASCII để debug. Khi hệ thống ổn định, có thể thêm binary frame:

- Start byte
- Sequence id
- Command id
- Payload length
- Payload
- CRC16
