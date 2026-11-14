# Giao thức UART — Máy giải Rubik 3×3×3

**Mục đích:** Điều khiển Rubik, từng servo, hiệu chỉnh và cấu hình hệ thống.

## 1. Cấu trúc gói lệnh

```text
#<ID> <GROUP> <ACTION> [ARGUMENTS...]\n
```

| Trường | Ý nghĩa |
|---|---|
| `#` | Ký tự bắt đầu gói lệnh |
| `ID` | Số thứ tự yêu cầu (sequence ID), từ `0` đến `65535` |
| `GROUP` | Nhóm lệnh, ví dụ `RUBIK`, `CONTROL`, `CALIB`, `CONFIG`, `SYSTEM` |
| `ACTION` | Hành động cần thực hiện; một số nhóm có thêm tiểu nhóm `SERVO` |
| `ARGUMENTS` | Tham số tùy theo lệnh |
| `\n` | Kết thúc gói lệnh; chấp nhận `\r\n` |

Ví dụ:

```text
#1 RUBIK MOVE L 500
#2 CONTROL SERVO 0 HOME
#3 CALIB SERVO SET 0 HOME 310
```

**Quy ước:** `ID` là số thứ tự giao dịch, **không phải mã nhóm lệnh**. Không tái sử dụng ID khi yêu cầu cũ chưa kết thúc. Chuỗi lệnh dùng ASCII, phân tách bằng khoảng trắng; từ khóa viết hoa. Mỗi lệnh kết thúc bằng byte `0A` (`\n`).

### Kiểm tra bằng RealTerm

Chọn đúng cổng COM, 115200 baud, 8N1, không flow control. Nối TX của USB–UART vào PA10 (STM32 RX), RX vào PA9 (STM32 TX), và nối chung GND.

Sau reset, STM32 gửi `I am alive` trước khi khởi tạo servo. Chờ khoảng 7 giây để khởi tạo cơ cấu hoàn tất rồi thử `PING`.

Trong tab Send, dùng **Send ASCII** với `#1 RUBIK PING` và bật thêm LF. Hoặc dùng **Send Numbers** với dãy sau (đã có LF ở cuối, không cần thêm EOL):

```text
0x23 0x31 0x20 0x52 0x55 0x42 0x49 0x4B 0x20 0x50 0x49 0x4E 0x47 0x0A
```

Với Send Numbers, dùng tiền tố `0x` để chỉ rõ số hex; không nhập dãy hex trần `23 31 20 ...`. Phản hồi mong đợi là `#1 OK` rồi `#1 DONE`. Dòng `I am alive` chỉ xác nhận đường phát từ STM32; chưa xác nhận đường nhận vào PA10.

## 2. Nhóm RUBIK — Điều khiển toàn bộ cơ cấu

### Cú pháp

```text
#<ID> RUBIK PING
#<ID> RUBIK RESET
#<ID> RUBIK MOVE <face> <duration_ms>
#<ID> RUBIK STOP
```

### Tham số

| Tham số | Giá trị | Mô tả |
|---|---|---|
| `face` | `U`, `D`, `L`, `R`, `F`, `B`, `U_`, `D_`, `L_`, `R_`, `F_`, `B_` | Mặt Rubik cần xoay |
| `duration_ms` | Số nguyên dương, giới hạn do firmware quy định | Thời lượng yêu cầu cho thao tác, đơn vị ms |


### Ví dụ

```text
#10 RUBIK RESET
#11 RUBIK MOVE L 500
#12 RUBIK MOVE R_ 600
#13 RUBIK MOVE U 800
#14 RUBIK STOP
```

**Chú ý:** `RESET` chỉ đưa cơ cấu về trạng thái chuẩn nếu điều kiện kẹp an toàn cho phép. `STOP` phải được ưu tiên xử lý; không được mặc định nhả tất cả tay kẹp khi dừng.

## 3. Nhóm CONTROL — Điều khiển từng servo

### Cú pháp

```text
#<ID> CONTROL SERVO <servo_id> <position>
```

### Quy ước ID

| `servo_id` | Loại | Vị trí hợp lệ |
|---|---|---|
| `0`–`3` | Servo xoay (`ROTATE`) | `HOME`, `CLOCK`, `ANTI` |
| `4`–`7` | Servo kẹp/trượt (`MOVE`) | `FULL_RELEASE`, `HALF_RELEASE`, `CLAMP`, `TIGHT_CLAMP` |

STM32 suy ra loại servo từ ID và kiểm tra vị trí hợp lệ. Firmware còn phải kiểm tra trạng thái cơ khí trước khi thực hiện lệnh.

### Ví dụ

```text
#20 CONTROL SERVO 0 HOME
#21 CONTROL SERVO 1 CLOCK
#22 CONTROL SERVO 2 ANTI
#23 CONTROL SERVO 4 CLAMP
#24 CONTROL SERVO 5 TIGHT_CLAMP
#25 CONTROL SERVO 6 HALF_RELEASE
#26 CONTROL SERVO 7 FULL_RELEASE
```

## 4. Nhóm CALIB — Hiệu chỉnh servo và tham số cơ khí

### 4.1. Bắt đầu phiên hiệu chỉnh

```text
#<ID> CALIB START
```

STM32 kiểm tra trạng thái an toàn, sao lưu cấu hình hiện tại vào **snapshot RAM** và chuyển sang `CALIB_MODE`.

### 4.2. Hiệu chỉnh vị trí servo

```text
#<ID> CALIB SERVO SET <servo_id> <position> <target>
#<ID> CALIB SERVO ADD <servo_id> <position> <offset>
#<ID> CALIB SERVO SUB <servo_id> <position> <offset>
#<ID> CALIB SERVO GET <servo_id> <position>
```

| Hành động | Ý nghĩa |
|---|---|
| `SET` | Gán giá trị vị trí bằng `target` |
| `ADD` | Tăng giá trị vị trí thêm `offset` |
| `SUB` | Giảm giá trị vị trí đi `offset` |
| `GET` | Đọc giá trị vị trí đang được cấu hình |

`target` và `offset` mặc định tính bằng **PWM count của PCA9685** (không phải góc độ), phải được giới hạn và kiểm tra trước khi áp dụng.

Ví dụ:

```text
#30 CALIB START
#31 CALIB SERVO SET 0 HOME 310
#32 CALIB SERVO ADD 0 CLOCK 5
#33 CALIB SERVO SUB 4 CLAMP 10
#34 CALIB SERVO GET 0 HOME
```

**Quy tắc an toàn:** `SET`/`ADD`/`SUB` chỉ cập nhật cấu hình trong RAM; **không tự động dịch chuyển servo**. Nếu cần xem trước vị trí mới, phải thiết kế một lệnh preview riêng có kiểm tra giới hạn.

### 4.3. Hiệu chỉnh tham số chung

```text
#<ID> CALIB SET <variable> <value>
#<ID> CALIB GET <variable>
```

Ví dụ (tên biến chỉ mang tính minh họa, cần định nghĩa trong firmware):

```text
#35 CALIB SET SERVO_STEP_MS 5
#36 CALIB GET SERVO_STEP_MS
```

Chỉ nên đặt trong `CALIB` các tham số thực sự phục vụ hiệu chỉnh cơ khí; tham số vận hành thông thường thuộc `CONFIG`.

### 4.4. Lưu, khôi phục, thoát

```text
#<ID> CALIB SAVE
#<ID> CALIB RESET
#<ID> CALIB EXIT
```

| Lệnh | Ý nghĩa |
|---|---|
| `CALIB SAVE` | Kiểm tra tính hợp lệ, ghi dữ liệu xuống Flash và kết thúc phiên |
| `CALIB RESET` | Khôi phục snapshot RAM tạo tại `CALIB START`, sau đó kết thúc phiên |
| `CALIB EXIT` | Thoát mà không lưu; hủy các thay đổi chưa lưu |

Nếu muốn trở về giá trị xuất xưởng, nên thiết kế lệnh khác (`CALIB FACTORY_RESET`) và có cơ chế xác nhận để tránh xóa nhầm thông số.

### 4.5. Ba bộ dữ liệu hiệu chỉnh

- **Active Calibration:** Thông số đang được sử dụng trong RAM.
- **Backup Calibration:** Snapshot lưu lúc `CALIB START` để rollback.
- **Saved Calibration:** Thông số lưu trong Flash, tồn tại sau khi mất nguồn.

`CALIB SAVE` nên lưu kèm phiên bản dữ liệu, checksum/CRC và kiểm tra giới hạn hợp lệ. Sau khi khởi động, firmware đọc bản cấu hình hợp lệ từ Flash. Snapshot RAM không tồn tại sau khi mất nguồn.

## 5. Nhóm CONFIG — Cấu hình tham số vận hành

### Cú pháp

```text
#<ID> CONFIG SET <variable> <value>
#<ID> CONFIG GET <variable>
#<ID> CONFIG SAVE
```

Ví dụ:

```text
#40 CONFIG SET UART_TIMEOUT_MS 1000
#41 CONFIG GET UART_TIMEOUT_MS
#42 CONFIG SAVE
```

`CONFIG SET` cập nhật RAM; `CONFIG SAVE` mới ghi vào Flash để tránh ghi liên tục. Danh sách biến và phạm vi giá trị phải được firmware định nghĩa cụ thể.



## 7. Phản hồi từ STM32

### Cú pháp phản hồi

```text
#<ID> OK
#<ID> DONE
#<ID> VALUE <value>
#<ID> ERR <error_code>
```

| Trạng thái | Ý nghĩa |
|---|---|
| `OK` | Cú pháp và điều kiện hợp lệ; yêu cầu đã được chấp nhận |
| `DONE` | Thao tác hoàn tất thành công |
| `VALUE` | Kết quả trả về cho lệnh đọc (`GET`) |
| `ERR` | Lệnh bị từ chối hoặc thực thi lỗi |

Với lệnh thay đổi/chuyển động, STM32 có thể trả `OK` rồi `DONE`. Với `GET`, `VALUE` là phản hồi hoàn tất; không cần `DONE` lần nữa.

### Ví dụ

```text
TX: #50 RUBIK MOVE L 500
RX: #50 OK
RX: #50 DONE

TX: #51 CALIB SERVO GET 0 HOME
RX: #51 VALUE 310

TX: #52 CONTROL SERVO 4 CLOCK
RX: #52 ERR INVALID_POSITION
```

### Mã lỗi đề xuất

| Mã lỗi | Ý nghĩa |
|---|---|
| `BAD_FORMAT` | Chuỗi sai định dạng |
| `UNKNOWN_CMD` | Không tồn tại nhóm hoặc hành động |
| `BAD_ARG` | Thiếu hoặc sai kiểu tham số |
| `INVALID_POSITION` | Servo/vị trí không hợp lệ |
| `LIMIT` | Giá trị vượt giới hạn |
| `BUSY` | Cơ cấu đang bận |
| `NOT_IN_CALIB_MODE` | Chưa vào chế độ hiệu chỉnh |
| `UNSAFE_STATE` | Trạng thái cơ khí không cho phép |
| `SAVE_FAILED` | Không thể lưu Flash |

## 8. Danh sách lệnh tổng hợp

```text
#<ID> RUBIK RESET
#<ID> RUBIK MOVE <face> <duration_ms>
#<ID> RUBIK STOP

#<ID> CONTROL SERVO <servo_id> <position>

#<ID> CALIB START
#<ID> CALIB SERVO SET <servo_id> <position> <target>
#<ID> CALIB SERVO ADD <servo_id> <position> <offset>
#<ID> CALIB SERVO SUB <servo_id> <position> <offset>
#<ID> CALIB SERVO GET <servo_id> <position>
#<ID> CALIB SET <variable> <value>
#<ID> CALIB GET <variable>
#<ID> CALIB SAVE
#<ID> CALIB RESET
#<ID> CALIB EXIT

#<ID> CONFIG SET <variable> <value>
#<ID> CONFIG GET <variable>
#<ID> CONFIG SAVE

#<ID> SYSTEM STATUS
#<ID> SYSTEM STOP
#<ID> SYSTEM VERSION
```

## 9. Kiến trúc xử lý STM32

```text
Raspberry Pi
    |
    v
UART Receiver (ISR)
    |
    v
Frame Parser (# ... \n)
    |
    v
Command Parser (ID, GROUP, ACTION, ARGS)
    |
    v
Command Dispatcher
    |
    +--> Rubik_CommandHandler()
    +--> Control_CommandHandler()
    +--> Calibration_CommandHandler()
    +--> Config_CommandHandler()
    +--> System_CommandHandler()
    |
    v
Điều khiển cơ cấu / cập nhật cấu hình / phản hồi UART
```

**Nguyên tắc triển khai:** Không thực thi chuyển động dài trong UART ISR; ISR chỉ nhận dữ liệu. Parser phải kiểm tra độ dài chuỗi và số lượng tham số.

---

Hiện tại không cần lưu flash các giá trị, không cần kiểm tra trạng thái hợp lệ của hệ thống của các servo. Đối với chế độ calib, đừng dùng ram gì quá phức tạp, hãy tạo ra các biến tạm tất cả các biến tạm lưu giá trị hiện tại của các servo, nếu cần save thì gán lại vào.

Hãy xử lí câu lệnh theo kiểu case, đọc các tham số rồi phân loại trường hợp case để xử lí với giá trị lệnh tương ứng
Đối với lệnh RUBIK MOVE L có nghĩa là L trong quy ước Rubik tức xoay cùng chiều kim đồng hồ, L_ là quay ngược chiều kim đồng hồ.

## 10. Triển khai hiện tại

Phần này áp dụng các yêu cầu giản lược ở cuối mục 9: chỉ lưu RAM, không kiểm tra trạng thái cơ khí, không ghi Flash.

| File | Trách nhiệm |
|---|---|
| `UART_Handle.c/.h` | Nhận từng byte bằng interrupt, ghép một dòng lệnh, phản hồi và gọi xử lý trong main loop |
| `UART_Command.c/.h` | Tách token, kiểm tra ID, phân loại nhóm bằng `switch/case` và gọi handler |
| `Rubik_Command.c/.h` | `PING`, `RESET`, `MOVE`, `STOP`; gọi thư viện `Rubik_Control` |
| `Control_Command.c/.h` | Gọi `Servo_Rotate` hoặc `Servo_Move` đúng loại servo |
| `Calibration_Command.c/.h` | Giữ offset tạm, xử lý hiệu chỉnh và gán offset khi `SAVE` |
| `Config_Command.c/.h` | Cấu hình thời gian nhận UART |
| `System_Command.c/.h` | `STATUS`, `STOP`, `VERSION` |

Giữ nguyên cách gọi hiện có trong `main.c`: `UART_Command_Init(&huart1)`, chuyển tiếp `HAL_UART_RxCpltCallback` vào `UART_Command_RxCallback`, rồi gọi `UART_Command_Process()` trong vòng lặp chính. Module UART đã định nghĩa `HAL_UART_ErrorCallback`; nếu ứng dụng bổ sung callback này ở nơi khác, chuyển tiếp vào `UART_Command_ErrorCallback` và chỉ giữ một định nghĩa callback HAL.

Thêm nhóm mới bằng một cặp `.h/.c`, bổ sung tên nhóm trong parser và một `case` trong `UART_DispatchCommand`. STM32CubeIDE đã đưa thư mục `Hardware` vào source path; refresh project rồi clean/build để nhận các file mới, không chỉnh các makefile tự sinh trong `Debug`.

### Các biến và giới hạn

| Biến/tham số | Phạm vi | Mặc định | Tác dụng |
|---|---|---|---|
| `CONFIG UART_TIMEOUT_MS` | 1–60000 ms | 1000 | Bỏ khung đang nhận nếu khoảng cách giữa hai byte vượt giới hạn |
| `CALIB SERVO_SETTLE_MS` | 1–60000 ms | `Delay_Servo_Move` (1000) | Thời gian đợi sau lệnh `CONTROL SERVO`; áp dụng khi `CALIB SAVE` |
| PWM hiệu chỉnh | 102–511 count | Theo cấu hình servo hiện tại | Chuyển đổi sang offset góc theo `min_pulse/max_pulse` của PCA9685 |
| `MOVE duration_ms` | 1–60000 ms | Bắt buộc truyền | Chỉ kiểm tra giá trị; thời gian thực tế vẫn do delay của `Rubik_Control` quyết định |

`SERVO_STEP_MS` trong ví dụ mục 4.3 chỉ mang tính minh họa và chưa được định nghĩa: thư viện hiện không nội suy chuyển động theo bước. Biến được hỗ trợ là `SERVO_SETTLE_MS`, ví dụ `#35 CALIB SET SERVO_SETTLE_MS 500`.

`CALIB START` sao chép các offset hiện tại vào mảng tạm. `GET` đọc giá trị tạm khi đang hiệu chỉnh, đọc cấu hình đang dùng khi ngoài phiên. `SET/ADD/SUB` chỉ sửa offset tạm; `SAVE` gán offset tạm vào `servo[]` và thoát phiên. `RESET/EXIT` bỏ dữ liệu tạm và thoát. Các lệnh này không gửi PWM; `CONTROL` và `RUBIK` tiếp tục dùng cấu hình đã lưu, cho đến lần `SAVE`. `CONFIG SET` áp dụng ngay trong RAM; `CONFIG SAVE` xác nhận cấu hình RAM, không ghi Flash. Mất nguồn sẽ mất mọi hiệu chỉnh và cấu hình UART đã thay đổi.

### Giới hạn của thư viện hiện có

- `Rubik_Down_ToFront()` đang rỗng: `MOVE D_` trả `ERR NOT_IMPLEMENTED`, không báo hoàn tất giả. Các mặt khác gọi đúng hàm hiện có; UART không sửa thuật toán chuyển động trong thư viện.
- Chỉ nhận và xử lý một lệnh mỗi lần, không có hàng đợi. Raspberry Pi phải chờ `DONE`, `VALUE` hoặc `ERR` trước khi gửi lệnh tiếp theo (`OK` mới là xác nhận tiếp nhận). Dữ liệu đến khi lệnh trước đang chờ xử lý hoặc đang chạy sẽ bị bỏ, không phản hồi.
- Các hàm Rubik đang blocking. `STOP` chỉ được nhận khi UART rảnh và giữ nguyên PWM/tay kẹp; không thể ngắt chuyển động đang chạy. `STATUS` trả `IDLE` hoặc `CALIB` khi được xử lý.
- Buffer chứa tối đa 63 byte sau `#`, trước `\n` (bao gồm `\r` nếu dùng CRLF). Dòng quá dài, chứa byte NUL, hoặc nhận chưa đủ mà timeout sẽ bị bỏ. Dòng sai định dạng/tham số trả `ERR`; ID không đọc được dùng ID `0`.
- UART truyền phản hồi đồng bộ với timeout 20 ms. `DONE` xác nhận hàm thư viện đã trả về sau thời gian chờ, không xác nhận phản hồi vị trí servo hoặc thành công I2C vì driver hiện không cung cấp thông tin này.

### Kiểm thử

Chạy từ thư mục gốc firmware:

```text
python Hardware/UART_Handle/Tests/run_tests.py
```

Cần GCC trên máy. Kiểm thử chạy parser và các handler với `Servo_Control` thật, sau đó chạy lại với cả `Rubik_Control` thật; chỉ giả lập HAL và đầu ra PCA9685. Bao gồm ánh xạ mặt/servo, nhận từng lệnh, giới hạn, chuyển đổi PWM và hiệu chỉnh tạm/lưu/hủy. File kiểm thử dùng đuôi `.inc` để không được CubeIDE biên dịch vào firmware.

