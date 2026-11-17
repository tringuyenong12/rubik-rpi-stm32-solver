# Giao thức UART — Máy giải Rubik STM32

Tài liệu mô tả mã nguồn hiện tại trong `UART_Handle`, `Rubik_Control` và `Servo_Control`. Các ví dụ là nội dung gửi tới STM32; mỗi dòng phải kết thúc bằng LF (byte `0A`).

## 1. Kết nối và cấu trúc gói lệnh

| Thuộc tính | Cấu hình |
|---|---|
| Ngoại vi | USART1 |
| TX / RX | PA9 / PA10 |
| Tốc độ | 115200 baud |
| Định dạng | 8 bit dữ liệu, không parity, 1 stop bit (8N1) |
| Điều khiển luồng phần cứng | Không |
| Kết thúc dòng | LF hoặc CRLF |

```text
#<ID> <GROUP> <ACTION> [ARGUMENTS...]\n
```

| Thành phần | Ý nghĩa |
|---|---|
| `#` | Bắt đầu khung; nhận `#` mới sẽ bắt đầu lại khung đang ghép |
| `ID` | Mã giao dịch thập phân 0–65535, tối đa 5 chữ số; phản hồi dùng lại ID |
| `GROUP` | Nhóm lệnh |
| `ACTION` | Hành động trong nhóm |
| `ARGUMENTS` | Tham số theo từng hành động |
| `\n` | Byte xuống dòng, không phải hai ký tự dấu gạch chéo và chữ n |

Ví dụ một gói đầy đủ:

```text
#27 CONTROL SERVO 02 CLOCK ANTI\n
```

Quy tắc truyền:

- Từ khóa phân biệt hoa/thường. Dùng đúng cách viết trong ví dụ; tên trường CALIB GET viết thường.
- Phân cách token bằng dấu cách ASCII, có thể dùng nhiều dấu cách. Parser chưa hỗ trợ tab.
- `<>` là tham số bắt buộc, `[]` là phần tùy chọn; không gửi các dấu này. Không gửi chú thích `// ...`.
- Buffer dài 64 byte: nhận tối đa 63 ký tự sau `#`, không tính CR/LF. Khung quá dài bị bỏ.
- Tối đa 10 token, bao gồm ID. Chỉ có một khung chờ, không có hàng đợi.
- Gửi từng lệnh, chờ `DONE` hoặc `ERR` trước khi gửi tiếp. Dữ liệu tới khi `cmd_ready` đang bật bị bỏ, kể cả khi servo đang chạy.

ID do bên gửi chọn, không quyết định nhóm lệnh. Firmware chưa quản lý chống trùng ID.

## 2. Các nhóm lệnh

| Nhóm | Chức năng | Trạng thái |
|---|---|---|
| `RUBIK` | Chu trình cơ cấu, xoay mặt đơn/cặp, chuẩn bị và đặt Rubik | Đã nối handler; riêng STOP chưa thực thi |
| `CONTROL` | Điều khiển servo đơn hoặc cặp | Đã nối handler |
| `CALIB` | Hiệu chỉnh offset theo độ và đọc thông số | Đã nối handler; lưu RAM |
| `CONFIG` | Dự kiến cấu hình hệ thống | Chưa triển khai; lời gọi handler đang comment |
| `SYSTEM` | Dự kiến lệnh hệ thống | Chưa triển khai; lời gọi handler đang comment |

## 3. Quy ước servo

| ID | Tên trong mã nguồn | Chức năng |
|---|---|---|
| 0 | `SERVO_ROTATE_FRONT` | Xoay FRONT |
| 1 | `SERVO_ROTATE_RIGHT` | Xoay RIGHT |
| 2 | `SERVO_ROTATE_BACK` | Xoay BACK |
| 3 | `SERVO_ROTATE_LEFT` | Xoay LEFT |
| 4 | `SERVO_MOVE_FRONT` | Kẹp/trượt FRONT |
| 5 | `SERVO_MOVE_RIGHT` | Kẹp/trượt RIGHT |
| 6 | `SERVO_MOVE_BACK` | Kẹp/trượt BACK |
| 7 | `SERVO_MOVE_LEFT` | Kẹp/trượt LEFT |

| Loại | Vị trí hợp lệ | Chức năng |
|---|---|---|
| ROTATE (0–3) | `HOME` | Về góc gốc |
| ROTATE (0–3) | `CLOCK` | Xoay cùng chiều kim đồng hồ |
| ROTATE (0–3) | `ANTI` | Xoay ngược chiều kim đồng hồ |
| MOVE (4–7) | `FULL_RELEASE` | Nhả hoàn toàn |
| MOVE (4–7) | `HALF_RELEASE` | Nhả một phần |
| MOVE (4–7) | `CLAMP` | Kẹp |
| MOVE (4–7) | `TIGHT_CLAMP` | Kẹp chặt |

Mỗi vị trí có góc cơ sở và offset riêng trong `servo[]`. Góc gửi ra bằng góc cơ sở cộng offset, được Servo_Control giới hạn về 0–180 độ. ID servo độc lập với kênh PCA9685 (`channel`).

## 4. Nhóm RUBIK

### 4.1. Lệnh cơ cấu

```text
#<ID> RUBIK PING
#<ID> RUBIK RESET
#<ID> RUBIK PREPARE
#<ID> RUBIK PUT
#<ID> RUBIK STOP
```

| Lệnh | Hoạt động thực tế |
|---|---|
| `PING` | Trả OK rồi DONE, không điều khiển servo |
| `RESET` | Nhả hoàn toàn cả bốn tay, chờ; đưa bốn trục xoay về HOME, chờ |
| `PREPARE` | Đưa bốn trục xoay về HOME, chờ; đưa cả bốn tay về CLAMP, chờ |
| `PUT` | Đưa bốn trục xoay về HOME, chờ; kẹp FRONT/RIGHT/BACK, nhả hoàn toàn LEFT (servo 7), chờ |
| `STOP` | Gọi `UART_Command_Stop()`, hiện là hàm rỗng: không dừng chuyển động, không trả phản hồi |

Các lệnh trên không nhận tham số bổ sung. RESET, PREPARE và PUT trả OK trước chu trình, DONE khi kết thúc. Khi khởi động, `main.c` cũng gọi `Rubik_Put()`.

### 4.2. Xoay mặt đơn

```text
#<ID> RUBIK MOVE <move>
```

| `move` | Hàm được gọi | Chức năng |
|---|---|---|
| `L`, `L_` | `Rubik_Left`, `Rubik_Left_` | Xoay LEFT thuận/ngược |
| `R`, `R_` | `Rubik_Right`, `Rubik_Right_` | Xoay RIGHT thuận/ngược |
| `F`, `F_` | `Rubik_Front`, `Rubik_Front_` | Xoay FRONT thuận/ngược |
| `B`, `B_` | `Rubik_Back`, `Rubik_Back_` | Xoay BACK thuận/ngược |
| `U`, `U_` | `Rubik_UpToFront`, `Rubik_Up_ToFront` | Đưa mặt UP về FRONT, xoay rồi hoàn nguyên cơ cấu |
| `D`, `D_` | `Rubik_DownToFront`, `Rubik_Down_ToFront` | Đưa mặt DOWN về FRONT, xoay rồi hoàn nguyên cơ cấu |

Dấu `_` sau tên mặt biểu thị chiều ngược. L/R/F/B thực hiện xoay, nhả tay tương ứng, trả trục về HOME rồi kẹp lại. U/D phối hợp nhiều tay. Các chu trình được thiết kế để bắt đầu từ trục HOME và tay CLAMP; firmware chưa kiểm tra điều kiện cơ khí trước khi chạy.

Handler chấp nhận thêm một token sau `move` nhưng bỏ qua token đó: `#11 RUBIK MOVE L 500` không đặt thời gian xoay 500 ms. Nên dùng `#11 RUBIK MOVE L`. Mỗi lần `waitUntilServosDone()` chờ cố định `Delay_Servo_Move = 1000` ms, không đọc cảm biến hoàn tất.

### 4.3. Xoay cặp mặt

| `move` | Trục thứ nhất | Trục thứ hai | Trạng thái cặp tay trượt khi kết thúc |
|---|---|---|---|
| `LR` | LEFT CLOCK | RIGHT CLOCK | CLAMP |
| `LR_` | LEFT CLOCK | RIGHT ANTI | FULL_RELEASE |
| `L_R` | LEFT ANTI | RIGHT CLOCK | FULL_RELEASE |
| `L_R_` | LEFT ANTI | RIGHT ANTI | FULL_RELEASE |
| `FB` | FRONT CLOCK | BACK CLOCK | FULL_RELEASE |
| `FB_` | FRONT CLOCK | BACK ANTI | FULL_RELEASE |
| `F_B` | FRONT ANTI | BACK CLOCK | FULL_RELEASE |
| `F_B_` | FRONT ANTI | BACK ANTI | FULL_RELEASE |

Hai trục nhận lệnh liên tiếp trước khi chờ. Sau bước xoay, cặp tay được nhả hoàn toàn và hai trục trở về HOME. Theo mã hiện tại, chỉ `Rubik_LR()` có bước kẹp lại; bảy hàm còn lại kết thúc sau bước HOME. Có thể gửi PREPARE để đưa cơ cấu về trạng thái kẹp trước lượt tiếp theo.

```text
#10 RUBIK PING
#11 RUBIK PUT
#12 RUBIK PREPARE
#13 RUBIK MOVE L
#14 RUBIK MOVE R_
#15 RUBIK MOVE LR
#16 RUBIK MOVE L_R
#17 RUBIK PREPARE
#18 RUBIK MOVE F_B_
#19 RUBIK PREPARE
```

MOVE hợp lệ trả OK, chạy hàm tương ứng rồi trả DONE. Các hàm Rubik không truyền kết quả lỗi servo về handler; DONE chỉ xác nhận chu trình phần mềm đã kết thúc.

## 5. Nhóm CONTROL

### 5.1. Servo đơn

```text
#<ID> CONTROL SERVO <servo_id> <position>
```

`servo_id` là 0–7, vị trí phải đúng loại ở mục 3. Servo đơn chỉ nhận một vị trí. Lệnh đưa servo tới vị trí yêu cầu, không tự thực hiện chu trình nhả/HOME/kẹp như RUBIK MOVE.

### 5.2. Cặp servo

```text
#<ID> CONTROL SERVO <pair_id> <position>
#<ID> CONTROL SERVO <pair_id> <position_1> <position_2>
```

| `pair_id` | Thứ tự servo | Loại vị trí |
|---|---|---|
| `02` | 0 FRONT, 2 BACK | ROTATE |
| `13` | 1 RIGHT, 3 LEFT | ROTATE |
| `46` | 4 FRONT, 6 BACK | MOVE |
| `57` | 5 RIGHT, 7 LEFT | MOVE |

Chỉ bốn token cặp trên được nhận diện. Giữ số 0 đầu trong `02`: đây là cặp 0 và 2. Một vị trí áp dụng chung cho cả hai; hai vị trí áp dụng lần lượt theo thứ tự chữ số của mã cặp.

```text
#20 CONTROL SERVO 0 HOME
#21 CONTROL SERVO 4 CLAMP
#22 CONTROL SERVO 02 HOME
#27 CONTROL SERVO 02 CLOCK ANTI
#28 CONTROL SERVO 13 ANTI CLOCK
#29 CONTROL SERVO 46 CLAMP
#30 CONTROL SERVO 57 CLAMP TIGHT_CLAMP
```

`02 CLOCK ANTI` điều khiển servo 0 CLOCK và servo 2 ANTI. `13 ANTI CLOCK` điều khiển servo 1 ANTI và servo 3 CLOCK.

Handler kiểm tra tất cả vị trí trước khi trả OK và gửi lệnh. Với cặp, cả hai servo nhận lệnh trước một lần chờ rồi trả DONE. Nếu hàm điều khiển báo thất bại, trả ERR EXEC_FAILED. Không có hoàn tác nếu một servo đã nhận lệnh còn servo kia lỗi.

## 6. Nhóm CALIB

CALIB chỉ xử lý servo đơn 0–7. Dùng ID đơn không thêm số 0 đầu để tránh nhầm: trong CALIB, `02` được phân tích thành số 2, không phải cặp.

### 6.1. Hiệu chỉnh vị trí

```text
#<ID> CALIB SERVO SET <servo_id> <position> <target_degree>
#<ID> CALIB SERVO ADD <servo_id> <position> <delta_degree>
#<ID> CALIB SERVO SUB <servo_id> <position> <delta_degree>
```

| Lệnh | Thay đổi |
|---|---|
| `SET` | Đặt offset = góc yêu cầu − góc cơ sở, để góc thực thi bằng target_degree |
| `ADD` | Cộng delta_degree vào offset hiện tại |
| `SUB` | Trừ delta_degree khỏi offset hiện tại |

Đơn vị là **độ**, không phải PWM count. Tham số là số thập phân trong 0–180, hỗ trợ phần lẻ như `0.5`; không nhận số mũ, hex, NaN hoặc Inf. Góc sau khi cộng offset cũng phải trong 0–180. Muốn giảm offset, dùng SUB với độ giảm không âm.

Handler trả OK, cập nhật offset trong RAM và điều khiển servo tới vị trí vừa hiệu chỉnh ngay, chờ rồi trả DONE. Góc cơ sở không thay đổi. Không ghi Flash; khởi động lại dùng giá trị khởi tạo trong mã nguồn. Không cần CALIB START/SAVE/EXIT.

```text
#31 CALIB SERVO SET 0 HOME 92
#32 CALIB SERVO ADD 0 HOME 0.5
#33 CALIB SERVO SUB 4 CLAMP 1
```

### 6.2. Đọc góc vị trí

```text
#<ID> CALIB SERVO GET <servo_id> <position>
#<ID> CALIB SERVO GET <servo_id> <position> REAL_ANGLE
```

Hai cú pháp đều trả góc cơ sở cộng offset. REAL_ANGLE không phải góc đo từ cảm biến; GET không gửi lệnh servo và không giới hạn tổng góc về 0–180.

```text
#34 CALIB SERVO GET 0 HOME
#35 CALIB SERVO GET 0 HOME REAL_ANGLE
```

### 6.3. Đọc trường thông số

```text
#<ID> CALIB SERVO GET <servo_id> <field_name>
```

| Loại | Tên trường hợp lệ |
|---|---|
| Tất cả servo | `channel`, `current_angle`, `target_angle` |
| ROTATE | `home_angle`, `offset_calib_home_angle`, `clockwise_angle`, `offset_calib_clockwise_angle`, `anticlockwise_angle`, `offset_calib_anticlockwise_angle` |
| MOVE | `full_release_angle`, `offset_calib_full_release_angle`, `half_release_angle`, `offset_calib_half_release_angle`, `clamp_angle`, `offset_calib_clamp_angle`, `tight_clamp_angle`, `offset_calib_tight_clamp_angle` |

`current_angle` lưu góc lệnh gần nhất; `target_angle` lưu góc PWM sau offset và giới hạn. Cả hai không phải phản hồi vị trí từ servo. Giá trị khởi tạo là -1; khi khởi động bình thường, PUT đã gửi lệnh nên có thể đã cập nhật.

```text
#36 CALIB SERVO GET 0 target_angle
#37 CALIB SERVO GET 0 offset_calib_home_angle
#38 CALIB SERVO GET 4 clamp_angle
#39 CALIB SERVO GET 4 channel
```

GET hợp lệ trả OK, VALUE với ba chữ số thập phân, rồi DONE. Ví dụ đọc channel 4 trả giá trị `4.000`.

## 7. Phản hồi và lỗi

Định dạng thực tế có `>` trước `#` và kết thúc bằng CRLF:

```text
>#<ID> OK\r\n
>#<ID> DONE\r\n
>#<ID> VALUE <value>\r\n
>#<ID> ERR <error_code>\r\n
```

| Phản hồi | Ý nghĩa |
|---|---|
| OK | Handler đã chấp nhận lệnh |
| DONE | Handler đã hoàn thành xử lý và các bước chờ |
| VALUE | Giá trị đọc; CALIB GET vẫn trả DONE phía sau |
| ERR | Lỗi tham số hoặc thực thi; có thể xuất hiện sau OK |

Ví dụ bỏ ký hiệu CR/LF để dễ đọc; giá trị CALIB phụ thuộc cấu hình và các lần hiệu chỉnh trước đó:

```text
TX: #27 CONTROL SERVO 02 CLOCK ANTI
RX: >#27 OK
RX: >#27 DONE

TX: #34 CALIB SERVO GET 0 HOME
RX: >#34 OK
RX: >#34 VALUE 92.500
RX: >#34 DONE

TX: #40 CONTROL SERVO 4 CLOCK
RX: >#40 ERR INVALID_POSITION
```

| Mã/trạng thái | Ý nghĩa |
|---|---|
| `ERR BAD_ARG` | Thiếu/thừa tham số hoặc sai định dạng |
| `ERR UNKNOWN_CMD` | Hành động không tồn tại trong nhóm đang xử lý |
| `ERR BAD_RUBIK_MOVE_ARG` | Tên bước xoay RUBIK không được hỗ trợ |
| `ERR INVALID_POSITION` | ID ngoài phạm vi hoặc vị trí/trường không hợp lệ |
| `ERR LIMIT` | Số CALIB vượt giới hạn hoặc góc kết quả không hợp lệ |
| `ERR EXEC_FAILED` | Hàm servo báo lỗi hoặc kênh không hợp lệ |
| `UNKNOWN_GROUP` | Parser không nhận diện nhóm; trả trực tiếp, không có tiền tố ERR |
| `BAD ARGC` | Parser có ID nhưng thiếu nhóm; trả trực tiếp, không có tiền tố ERR |

ID sai định dạng và khung quá dài bị bỏ mà không phản hồi. Không có phản hồi BUSY. CONFIG, SYSTEM và RUBIK STOP hiện không trả phản hồi; không dùng các lệnh này trong luồng chờ DONE.

Khi khởi động, chương trình gửi riêng dòng `Hello from alive STM32 USART1`; đây không phải phản hồi có ID.

## 8. Luồng xử lý và giới hạn hiện tại

```text
USART1 RX interrupt
    -> HAL_UART_RxCpltCallback() trong main.c
    -> UART_Command_RxCallback(): ghép khung # ... LF
    -> cmd_ready = true
Main loop
    -> UART_Command_Process()
    -> UART_ParseCommand(): tách token, đọc ID và chọn nhóm
    -> Rubik_CommandHandler / Control_CommandHandler / Calibration_CommandHandler
    -> Rubik_Control / Servo_Control / PCA9685
    -> phản hồi trên USART1
```

| File | Trách nhiệm |
|---|---|
| `Core/Src/main.c` | Cấu hình UART, khởi tạo, chuyển tiếp callback RX và gọi Process trong vòng lặp |
| `UART_Handle.c/.h` | Nhận byte, ghép khung, tách token, chọn nhóm, gửi phản hồi |
| `Rubik_Command.c/.h` | Phân loại RUBIK và gọi chu trình cơ cấu |
| `Control_Command.c/.h` | Kiểm tra ID/vị trí, điều khiển servo đơn/cặp |
| `Calibration_Command.c/.h` | Chỉnh offset trong RAM, áp dụng góc và đọc thông số |
| `Config_Command.c/.h`, `System_Command.c/.h` | File khung, chưa triển khai chức năng |
| `Hardware/Rubik_Control/Rubik_Control.c/.h` | Các chu trình phối hợp servo |
| `Hardware/Servo_Control/Servo_Control.c/.h` | Ánh xạ servo, góc/offset và gửi góc tới PCA9685 |

Chuyển động chạy blocking trong main loop. Firmware chưa kiểm tra trạng thái kẹp hay chống va chạm; DONE dựa trên xử lý phần mềm và độ trễ cố định. Driver PCA9685 hiện không trả lỗi I2C về lớp servo, nên DONE không xác nhận chuyển động vật lý thành công.

Các điểm cần lưu ý khi bảo trì parser: biến `command_id` trong `UART_ParseCommand()` đang là `unsigned int`, trong khi `UART_ParseId()` nhận `uint16_t *`; cần thống nhất kiểu để ID phản hồi được bảo đảm. Parser cũng truy cập token ID trước khi kiểm tra số token, nên khung chỉ dấu cách hoặc quá nhiều token chưa được xử lý chắc chắn. Các điểm này được ghi nhận ở đây; tài liệu không thay đổi mã thực thi.

Các lệnh chưa hỗ trợ gồm CALIB START/SAVE/RESET/EXIT, CALIB SET/GET tham số chung, CONFIG SET/GET/SAVE và SYSTEM STATUS/STOP/VERSION. Khai báo hàm trong header không đồng nghĩa chức năng đã được nối vào luồng UART.
