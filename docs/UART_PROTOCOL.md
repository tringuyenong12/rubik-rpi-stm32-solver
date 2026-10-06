# UART Protocol RPi <-> STM32

## Cau Hinh Mac Dinh

- Baudrate: 115200
- Data bits: 8
- Parity: none
- Stop bits: 1
- Line ending: `\n`
- Encoding: ASCII/UTF-8

## Lenh

### PING

```text
PING
```

Phan hoi:

```text
OK PONG
```

### HOME

```text
HOME
```

Phan hoi:

```text
OK HOME
DONE HOME
```

### MOVE

```text
MOVE <face> <turns> <duration_ms>
```

Trong do:

- `face`: `U`, `R`, `F`, `D`, `L`, `B`
- `turns`: `1` la 90 do thuan, `-1` la 90 do nghich, `2` la 180 do
- `duration_ms`: thoi gian servo thuc hien action

Vi du:

```text
MOVE R 1 450
MOVE U -1 450
MOVE F 2 700
```

Phan hoi:

```text
OK MOVE
DONE MOVE
```

### SERVO

Dung cho calibration tung servo.

```text
SERVO <channel> <pulse_us> <duration_ms>
```

Vi du:

```text
SERVO 0 1500 300
```

### STOP

```text
STOP
```

Phan hoi:

```text
OK STOP
```

## Lenh Mo Rong Theo Ban Ve Co Khi

Theo ban ve CAD hien tai, robot co 4 cum truot cheo va cum trung tam. Cac lenh duoi day phu hop hon cho giai doan tich hop co khi.

### ACTUATOR

Di chuyen mot actuator logic den target.

```text
ACTUATOR <role> <target> <duration_ms>
```

Vi du:

```text
ACTUATOR carriage_nw home 800
ACTUATOR carriage_ne approach 500
ACTUATOR center_lift scan 700
```

Role de xuat:

- `carriage_nw`
- `carriage_ne`
- `carriage_sw`
- `carriage_se`
- `center_lift`
- `center_rotate`

Target de xuat:

- `home`
- `approach`
- `engaged`
- `retract`
- `scan`
- `solve`
- `safe`

### CLAMP

Dong/mo dau kep hoac dau tac dong.

```text
CLAMP <role> <open|close>
```

Vi du:

```text
CLAMP tool_nw close
CLAMP tool_nw open
```

### TURN

Lenh xoay mot mat Rubik theo abstraction co khi. `TURN` nen thay the `MOVE` khi bat dau tich hop co khi that.

```text
TURN <face> <turns> <duration_ms>
```

Vi du:

```text
TURN R 1 450
TURN U -1 450
```

### SCAN_POSE

Dua cube ve tu the de camera chup mot mat.

```text
SCAN_POSE <face>
```

Vi du:

```text
SCAN_POSE U
SCAN_POSE F
```

## Loi

```text
ERR <code> <message>
```

Code de xuat:

- `BAD_CMD`: sai lenh.
- `BAD_ARG`: sai tham so.
- `BUSY`: STM32 dang thuc thi.
- `LIMIT`: goc servo vuot gioi han.
- `TIMEOUT`: action qua thoi gian an toan.

## Nang Cap Sau

ASCII de debug. Khi he thong on dinh, co the them binary frame:

- Start byte
- Sequence id
- Command id
- Payload length
- Payload
- CRC16

