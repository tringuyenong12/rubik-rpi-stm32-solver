# Actuator Mapping

Tài liệu này định nghĩa cách đặt tên actuator theo bản vẽ CAD. Đây là mapping logic cho phần mềm; channel STM32 thực tế sẽ được điền sau khi chốt motor/driver.

## Tên Actuator

| Role | Vị Trí Suy Luận | Chức Năng |
|---|---|---|
| `carriage_nw` | Cụm trượt góc trên-trái theo camera top-down | Tiến/lùi đầu tác động vào cube |
| `carriage_ne` | Cụm trượt góc trên-phải theo camera top-down | Tiến/lùi đầu tác động vào cube |
| `carriage_sw` | Cụm trượt góc dưới-trái theo camera top-down | Tiến/lùi đầu tác động vào cube |
| `carriage_se` | Cụm trượt góc dưới-phải theo camera top-down | Tiến/lùi đầu tác động vào cube |
| `tool_nw` | Đầu tác động trên carriage_nw | Kẹp, giữ, hoặc xoay mặt Rubik |
| `tool_ne` | Đầu tác động trên carriage_ne | Kẹp, giữ, hoặc xoay mặt Rubik |
| `tool_sw` | Đầu tác động trên carriage_sw | Kẹp, giữ, hoặc xoay mặt Rubik |
| `tool_se` | Đầu tác động trên carriage_se | Kẹp, giữ, hoặc xoay mặt Rubik |
| `center_lift` | Cụm dưới mặt bàn | Nâng/hạ hoặc đưa cube vào vị trí scan |
| `center_rotate` | Cụm dưới mặt bàn | Xoay/định hướng cube nếu có |

## Trạng Thái Đề Xuất

Mỗi actuator nên có trạng thái logic:

```text
UNKNOWN
HOMING
HOME
MOVING
ENGAGED
RETRACTED
ERROR
STOPPED
```

## Lệnh UART Mở Rộng Đề Xuất

Lệnh debug hiện có:

```text
SERVO <channel> <pulse_us> <duration_ms>
MOVE <face> <turns> <duration_ms>
```

Lệnh phù hợp hơn với bản vẽ:

```text
ACTUATOR <role> <target> <duration_ms>
CLAMP <role> <open|close>
TURN <face> <turns> <duration_ms>
SCAN_POSE <face>
HOME
STOP
```

Ví dụ:

```text
ACTUATOR carriage_nw approach 500
CLAMP tool_nw close
TURN R 1 450
CLAMP tool_nw open
ACTUATOR carriage_nw retract 500
```

## Mapping Cube Face Sang Cơ Khí

Chưa nên hard-code cho đến khi test thật. Ban đầu dùng bảng sau:

| Cube Face | Tool/Carriage Dự Kiến | Ghi Chú |
|---|---|---|
| U | TBD | Có thể cần center_rotate/reorient |
| R | TBD | Cần test đầu tác động gần mặt phải |
| F | TBD | Cần test góc nhìn camera và hướng cube |
| D | TBD | Có thể liên quan center_lift/rotate |
| L | TBD | Cần test đầu tác động gần mặt trái |
| B | TBD | Có thể cần reorient cube |

Sau khi có hardware thật, điền bảng này trước khi tối ưu motion planner.
