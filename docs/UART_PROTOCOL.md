# UART Protocol RPi <-> STM32

Firmware chính tại `firmware/stm32cubeide` và phần mềm Raspberry Pi dùng giao thức dưới đây. Module `App/rubik_protocol` xử lý frame, còn `App/UART_Handle` gọi phần cứng và gửi phản hồi. Xem thêm [hướng dẫn UART firmware](../firmware/stm32cubeide/App/UART_Handle/README.md).

## Cấu hình và cú pháp

115200 baud, 8 data bits, không parity, 1 stop bit, không flow control.
Khung ASCII kết thúc bằng `\n` (STM32 cũng nhận CRLF), tối đa 95 ký tự
không tính ký tự kết thúc dòng.

```text
#<tagname> <tên hàm> <thao tác> [tham số]
#567 RUBIK MOVE L
```

- Tag: 1–32 ký tự chữ ASCII, số, `_` hoặc `-`, phân biệt hoa/thường.
- `RUBIK`: nhóm hàm được parser định tuyến đến bộ xử lý Rubik.
- `MOVE`: thao tác; `L`: tham số mặt cần xoay.
- Tên nhóm hàm và thao tác phân biệt hoa/thường, dài 1–24 ký tự ASCII:
  bắt đầu bằng chữ hoặc `_`, tiếp theo là chữ, số hoặc `_`.
  Nhóm RUBIK dùng thao tác và mặt viết hoa. Không truyền địa chỉ con trỏ qua UART.
- Mỗi yêu cầu dùng tag riêng. Pi tự sinh tag nếu không chỉ định.

## ACK xác nhận liên kết

Tên nhóm hàm là tham số `function`, mặc định `RUBIK` để giữ các lệnh cũ:

```python
command = Command("servo", (0, 1500, 300), function="CALIB")
print(command.to_wire(tag="578"))  # #578 CALIB servo 0 1500 300
```

STM32 lưu tên vào `command.function`, thao tác vào `command.operation`.
Nhóm CALIB đã hỗ trợ SERVO, SET và TEST. Ví dụ Python ở trên trả
`#578 ACK` rồi `#578 DONE`. Nhóm khác RUBIK/CALIB có kiểu
`RUBIK_CMD_CUSTOM`, với tham số dạng chuỗi trong `command.arguments`.
Thêm handler cho nhóm mới tại nhánh CUSTOM của UART_Command_Process.

Pi mặc định chờ ACK rồi DONE cho nhóm tùy chọn. Nếu handler chỉ trả ACK,
tạo lệnh với `wait_done=False`. Không cần sửa SerialLink khi thêm tên nhóm mới.

```text
Pi    -> #12 RUBIK PING
STM32 -> #12 ACK
```

ACK đúng tag xác nhận UART hoạt động hai chiều. `SerialLink.open()` tự thực
hiện bước này, chờ 2 giây/lần, thử tối đa 3 lần với các tag khác nhau.
Nếu không nhận ACK đúng tag, Pi đóng cổng, đặt `connected=False` và báo
`ConnectionError`. Mở được cổng serial chưa đủ để xác nhận liên kết.
Giao thức thay thế bản HELLO/OK; cần cập nhật cả Pi và STM32.

## Phản hồi cho từng lệnh

```text
Pi    -> #567 RUBIK MOVE L
STM32 -> #567 ACK
STM32 -> #567 DONE
```

ACK xác nhận nhận lệnh; DONE xác nhận thao tác hoàn tất. ACK không đảm bảo
thao tác thành công. Nếu phát hiện lỗi trước hoặc trong xử lý, STM32 trả:

```text
#567 NACK BAD_CMD move_args
```

NACK kết thúc yêu cầu, không gửi DONE; lỗi có thể xuất hiện sau ACK.
Mã lỗi hiện dùng gồm BAD_CMD, BAD_ARG, LIMIT, UNSUPPORTED và STOPPED. Nếu tag thiếu hoặc không hợp lệ,
trả `#? NACK BAD_CMD invalid_tag` vì không có tag để đối chiếu.
Khung quá dài bị loại bỏ và trả NACK; không thực thi phần đuôi khung.

Pi bỏ qua phản hồi khác tag, chờ ACK rồi DONE đúng tag. Chỉ gửi một yêu cầu
tại một thời điểm; không dùng chung SerialLink giữa nhiều luồng. Không tự
gửi lại chuyển động khi timeout vì lệnh có thể đã chạy. Firmware chưa có
bộ nhớ chống thực thi lặp khi bên gửi cố tình gửi lại tag.

## Các thao tác RUBIK

Mọi dòng dưới đây cần tiền tố `#tag RUBIK `.

| Thao tác | Tham số | Phản hồi thành công |
| --- | --- | --- |
| PING | Không | ACK |
| STOP | Không | ACK |
| HOME | Không | ACK, DONE |
| MOVE / TURN | `<face> [<turns> <duration_ms>]` | ACK, DONE |
| SERVO | `<channel> <pulse_us> <duration_ms>` | ACK, DONE |
| ACTUATOR | `<role> <target> <duration_ms>` | NACK UNSUPPORTED |
| CLAMP | `<role> <open hoặc close>` | NACK UNSUPPORTED |
| SCAN_POSE | `<face>` | NACK UNSUPPORTED |

Face: U, R, F, D, L, B. Turns: 1, -1 hoặc 2. `MOVE L` mặc định
turns=1, duration_ms=450. Khi chỉ định thời gian, cung cấp cả turns và
duration_ms: `#568 RUBIK MOVE L_ -1 600`.

Ký hiệu xoay ngược trên UART dùng `_` thay dấu nháy: `R'` → `R_`,
`L'` → `L_`, tương tự U, F, D, B. Ví dụ `#569 RUBIK MOVE R_`
xoay mặt R ngược chiều, mặc định 450 ms. Pi nhận công thức với cả dấu nháy
và dấu `_`, nhưng xuất UART bằng `_`. Nếu có tham số turns sau mặt có `_`,
turns phải là `-1` (không đảo chiều hai lần). Dạng cũ `MOVE R -1 450`
vẫn được STM32 chấp nhận. Ký hiệu xoay 180 độ trong công thức vẫn là `R2`.
MOVE/TURN gọi trực tiếp các chuỗi trong Rubik_Control. L, R, F, B có hai chiều, U có chiều thuận. U đảo và cả hai chiều D trả NACK UNSUPPORTED motion_incomplete vì code chuyển động còn lỗi hoặc thiếu. Lệnh cũ TEST_RUBIK MOVE được giữ tương thích và cũng nhận ACK/DONE/NACK.

Duration nhận số nguyên 0–60000 ms. Với MOVE/TURN, thời gian này là tổng thời gian tối thiểu, còn các bước servo dùng thời gian trong Servo_Control. Turns 2 thực hiện chuỗi thuận hai lần. SERVO điều khiển PCA9685 tại 50 Hz, nhận channel 0–15 và pulse_us 500–2500.

STOP khóa MOVE, TURN và SERVO cho đến khi HOME được thực hiện. Các chuỗi hiện chạy blocking nên STOP được xử lý sau khi chuỗi đang chạy hoàn tất. DONE xác nhận hàm điều khiển đã chạy xong, driver hiện chưa phản hồi lỗi I2C hoặc vị trí thực.

## Các thao tác CALIB

CALIB là nhóm hiệu chỉnh servo. Có ba thao tác với cú pháp sau; dấu `<...>`
chỉ tên tham số, không gõ dấu ngoặc khi gửi lệnh:

```text
#<tag> CALIB SET <servo_id> <position> <angle_deg>
#<tag> CALIB TEST <servo_id> <position> <duration_ms>
#<tag> CALIB SERVO <channel> <pulse_us> <duration_ms>
```

### Ý nghĩa từng tham số

| Tham số | Ý nghĩa | Giá trị hợp lệ |
| --- | --- | --- |
| `tag` | Mã yêu cầu do bên gửi đặt, để đối chiếu ACK/DONE/NACK; không phải ID servo | 1–32 ký tự chữ ASCII, số, `_`, `-` |
| `servo_id` | ID logic của servo trong mảng `servo[]` của Servo_Control.c | Số nguyên 0–7, xem bảng bên dưới |
| `position` | Tên vị trí cần chỉnh hoặc chạy thử; phải đúng loại servo | Tên viết hoa trong bảng bên dưới |
| `angle_deg` | Góc cuối mong muốn tại vị trí đó, tính bằng độ; không phải số độ xoay thêm và không phải offset | Số 0–180, cho phép thập phân bằng dấu chấm, ví dụ `92.5` |
| `duration_ms` | Thời gian chờ sau khi gửi góc/xung, tính bằng mili giây; 1000 ms = 1 giây; không điều chỉnh tốc độ quay | Số nguyên 0–60000 |
| `channel` | Kênh vật lý trên PCA9685, chỉ dùng với CALIB SERVO | Số nguyên 0–15 |
| `pulse_us` | Độ rộng xung điều khiển servo, tính bằng micro giây; 1500 us = 1,5 ms | Số nguyên 500–2500 tại tần số PWM 50 Hz |

Mọi tham số trong mỗi dạng lệnh đều bắt buộc. `SET`, `TEST` và tên vị trí
phải viết hoa. `SERVO` có thêm tên tương thích viết thường là `servo`.

### Chọn servo và vị trí

| `servo_id` | Servo được chọn | Các giá trị `position` |
| --- | --- | --- |
| 0 | Xoay mặt FRONT | HOME, CLOCKWISE, ANTICLOCKWISE |
| 1 | Xoay mặt RIGHT | HOME, CLOCKWISE, ANTICLOCKWISE |
| 2 | Xoay mặt BACK | HOME, CLOCKWISE, ANTICLOCKWISE |
| 3 | Xoay mặt LEFT | HOME, CLOCKWISE, ANTICLOCKWISE |
| 4 | Trượt tay FRONT | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |
| 5 | Trượt tay RIGHT | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |
| 6 | Trượt tay BACK | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |
| 7 | Trượt tay LEFT | FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP |

| `position` | Ý nghĩa | Góc cơ sở mặc định trong Servo_Control.c |
| --- | --- | --- |
| HOME | Vị trí ban đầu của servo xoay | 90° |
| CLOCKWISE | Vị trí quay thuận của servo xoay | 180° |
| ANTICLOCKWISE | Vị trí quay ngược của servo xoay | 0° |
| FULL_RELEASE | Nhả hoàn toàn tay trượt | 180° |
| HALF_RELEASE | Nhả một phần tay trượt | 90° |
| CLAMP | Kẹp Rubik | 10° |
| TIGHT_CLAMP | Kẹp chặt hơn để giữ Rubik | 0° |

Góc thực tế cần hiệu chỉnh theo cách lắp servo và cơ cấu của bạn. Ví dụ,
`SET 4 HOME 90` bị từ chối vì ID 4 là servo trượt, không có vị trí HOME.

SET/TEST dùng `servo_id`, sau đó driver lấy kênh từ `servo[servo_id].channel`.
CALIB SERVO dùng trực tiếp `channel`. Cấu hình mặc định gán ID 0–7 cho kênh
0–7, nhưng nếu đổi `.channel` trong Servo_Control.c thì hai số này có thể khác nhau.

### Cách SET và TEST hoạt động

`SET` gọi `Servo_SetRotateCalibration()` hoặc `Servo_SetMoveCalibration()`.
Lệnh chỉ sửa offset của đúng vị trí đã chọn trong RAM, không gửi PWM và không
làm servo chuyển động ngay. Công thức là:

```text
offset = angle_deg - góc cơ sở của position
```

Ví dụ `#c2 CALIB SET 0 HOME 92.5`: `c2` là mã yêu cầu; `0` chọn servo xoay
FRONT; `HOME` chọn góc ban đầu; `92.5` đặt góc cuối thành 92,5°. Với góc
cơ sở HOME là 90°, offset được lưu là +2,5°. Gửi lại SET sẽ thay offset,
không cộng dồn nó và không sửa các vị trí khác của servo.

`TEST` gọi `Servo_Rotate()` cho ID 0–3 hoặc `Servo_Move()` cho ID 4–7,
để chạy đến góc cơ sở cộng offset đã lưu. Sau đó gọi `waitUntilServosDone()`.
Driver hiện chờ `Delay_Servo_Move = 1000 ms`; nếu `duration_ms` lớn hơn,
CALIB chờ thêm phần còn lại. Vì vậy thời gian chờ trước DONE là ít nhất
`max(1000, duration_ms)` với driver hiện tại:

| Ví dụ | Tác dụng |
| --- | --- |
| `#c3 CALIB TEST 0 HOME 500` | Servo xoay FRONT đến HOME đã chỉnh; chờ ít nhất 1 giây |
| `#c6 CALIB TEST 0 HOME 1500` | Servo xoay FRONT đến HOME đã chỉnh; chờ ít nhất 1,5 giây |
| `#c5 CALIB TEST 4 CLAMP 0` | Servo trượt FRONT đến CLAMP đã chỉnh; vẫn chờ ít nhất 1 giây |

TEST cũng dùng được khi chưa gửi SET; lúc đó nó dùng các góc/offset hiện có
trong Servo_Control.c. DONE xác nhận phần mềm đã gửi lệnh và chờ xong;
không có cảm biến xác nhận servo đã đến đúng vị trí hoặc phản hồi lỗi I2C.

### Thử xung trực tiếp bằng SERVO

`#c1 CALIB SERVO 0 1500 300` có nghĩa: gửi xung 1500 us đến kênh PCA9685
số 0 ở 50 Hz, rồi chờ 300 ms trước DONE. Lệnh này đi thẳng đến PCA9685,
không dùng các vị trí HOME/CLAMP và không sửa góc/offset hoặc trạng thái
góc trong Servo_Control. Sau 300 ms, PWM vẫn giữ xung đã đặt; đây không
phải lệnh tắt servo sau 300 ms. Quy tắc chờ tối thiểu 1 giây của TEST
không áp dụng cho SERVO.

### Ví dụ gửi lần lượt

Chờ DONE hoặc NACK của từng lệnh trước khi gửi lệnh kế tiếp:

```text
#c1 CALIB SERVO 0 1500 300
#c2 CALIB SET 0 HOME 92.5
#c3 CALIB TEST 0 HOME 500
#c4 CALIB SET 4 CLAMP 12
#c5 CALIB TEST 4 CLAMP 500
```

Các lệnh đều trả ACK rồi DONE khi thành công. Ví dụ phản hồi của lệnh SET:

```text
#c2 ACK
#c2 DONE
```

```python
link.request(Command("SET", (0, "HOME", 92.5), function="CALIB"))
link.request(Command("TEST", (0, "HOME", 500), function="CALIB"))
```

SET tính offset bằng góc yêu cầu trừ góc cơ sở. Ví dụ HOME cơ sở 90 độ,
SET HOME 92.5 tạo offset +2.5 độ. Các chuỗi RUBIK dùng cấu hình mới ngay
ở lần điều khiển tiếp theo. Giá trị trở về cấu hình trong Servo_Control.c
sau reset hoặc mất điện. Có thể điền các offset tìm được vào mảng servo[]
trong file đó để giữ qua các lần khởi động.

STOP khóa CALIB TEST và CALIB SERVO cho đến RUBIK HOME. SET vẫn cập nhật
cấu hình khi đang STOP. Xem bảng mapping và luồng code trong
[hướng dẫn UART firmware](../firmware/stm32cubeide/App/UART_Handle/README.md).

## Sử dụng trên Pi

```bash
cd rpi
python -m rubik_robot.main --mode connect --port /dev/serial0
```

CLI báo KET NOI THANH CONG khi nhận ACK đúng tag, hoặc
KET NOI/LENH THAT BAI và mã thoát 1 khi lỗi.

```python
from rubik_robot.protocol import Command
from rubik_robot.transport.serial_link import SerialLink

with SerialLink("/dev/serial0") as link:
    result = link.request(Command("MOVE", ("L",)), tag="567")
    print(result)  # #567 DONE
    print(link.check_connection())  # PING mới, kiểm tra ACK cùng tag
```

Tag truyền vào Python không gồm dấu #. API từ chối dùng lại tag trong cùng
đối tượng SerialLink. `Command.to_wire(tag="567")` tạo khung đầy đủ;
`to_wire()` không có tag chỉ tạo phần thao tác để xem trước kế hoạch.
`request()` trả DONE với chuyển động, ACK với PING/STOP, hoặc phát sinh lỗi
khi nhận NACK/timeout. ACK dùng timeout_s mặc định 2 giây. DONE dùng thời gian chờ lớn hơn giữa timeout_s và motion_timeout_s, mặc định motion_timeout_s là 65 giây.

`check_connection()` kiểm tra theo yêu cầu, không có heartbeat nền.
connected phản ánh lần kiểm tra gần nhất; rút dây được phát hiện ở lần trao
đổi tiếp theo. Gọi open() để bắt tay lại sau khi mất liên kết.

Nối TX Pi với RX STM32, RX Pi với TX STM32, GND chung, mức logic 3.3 V.
Bật UART và tắt serial console trên cổng dùng ở Pi. Build/flash project chính tại firmware/stm32cubeide. Core/Src/main.c đã nối callback nhận, callback lỗi và vòng lặp xử lý UART. Chờ cơ cấu hoàn tất khởi động trước khi kết nối.
