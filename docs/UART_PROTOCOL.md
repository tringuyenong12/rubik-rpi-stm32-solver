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

```text
#c1 CALIB SERVO 0 1500 300
#c2 CALIB SET 0 HOME 92.5
#c3 CALIB TEST 0 HOME 500
#c4 CALIB SET 4 CLAMP 12
#c5 CALIB TEST 4 CLAMP 500
```

SERVO thử xung 500–2500 us trên kênh PCA9685 0–15. SET cập nhật góc cuối
0–180 độ của một vị trí servo trong RAM. TEST áp dụng vị trí đã chỉnh rồi
chờ thời gian yêu cầu. Các lệnh đều trả ACK rồi DONE khi thành công.

SET/TEST dùng servo_id 0–7. ID 0–3 là servo xoay FRONT, RIGHT, BACK, LEFT,
có các vị trí HOME, CLOCKWISE, ANTICLOCKWISE. ID 4–7 là servo trượt theo cùng
thứ tự, có FULL_RELEASE, HALF_RELEASE, CLAMP, TIGHT_CLAMP.

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
