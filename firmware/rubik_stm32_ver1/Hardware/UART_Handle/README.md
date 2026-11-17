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


### 4.1. Hiệu chỉnh vị trí servo

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


### 4.2. Hiệu chỉnh tham số chung

```text
#<ID> CALIB SET <variable> <value>
#<ID> CALIB GET <variable>
```

Ví dụ (tên biến chỉ mang tính minh họa, cần định nghĩa trong firmware):

```text
#35 CALIB SET SERVO_STEP_MS 5
#36 CALIB GET SERVO_STEP_MS
```

#1 CALIB SERVO SET 0 HOME 92
#2 CALIB SERVO ADD 0 HOME 0.5
#3 CALIB SERVO SUB 0 HOME 1
#4 CALIB SERVO GET 0 HOME
#5 CALIB SERVO GET 0 target_angle
#6 CALIB SERVO GET 0 offset_calib_home_angle


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
Command Parser (ID, GROUP, ACTION, ARGS, ...)
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



