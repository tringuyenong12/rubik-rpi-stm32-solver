# Auto Solve với camera trên cao

1. Build và nạp firmware từ project STM32CubeIDE `firmware/rubik_stm32_ver1`.
2. Đưa robot vào tư thế nạp khối. Có thể dùng `RUBIK PUT` trong terminal UART khi cơ cấu đã sẵn sàng cho thao tác này. Đóng terminal để giải phóng cổng.
3. Đặt Rubik ngay ngắn và căn thẳng các lớp. Màu mặt trên và mặt trước tùy ý.
4. Đặt camera phía trên sao cho cạnh trên ảnh hướng về phía sau máy và cạnh phải ảnh hướng về bên phải máy. Camera cần nhìn trọn chín ô và ảnh không lật gương. Nếu cần, căn ROI theo chỉ số camera trong Solve Guide.
5. Mở GUI, chọn **Auto Solve**, nhập cổng UART thực tế như `/dev/serial0` hoặc `/dev/ttyUSB0`, chọn baud 115200 và bấm **Start**.

Chạy GUI từ Desktop hoặc VNC của Raspberry Pi:

```bash
cd ~/rubik-rpi-stm32-solver
.venv-pi/bin/python -B scripts/run_vision_gui.py --camera 0 --backend v4l2
```

Trên Windows, dùng `.\.venv\Scripts\python.exe -B scripts/run_vision_gui.py --camera 1 --backend dshow` và chọn đúng cổng COM. Solver mặc định dùng `localhost:8080`. Nếu localhost từ chối kết nối, ứng dụng dùng solver tại chỗ.

Pi mở camera, gửi PING rồi gửi `RUBIK SCAN_BEGIN`. STM32 kiểm tra góc HOME đã ra lệnh và đóng kẹp trước khi Pi chụp mặt trên. Các lệnh tiếp theo đổi tư thế **toàn khối**. Mỗi lần chờ DONE, sau đó chờ ảnh ổn định 0,4 giây và lấy ít nhất 12 mẫu trong ít nhất 1,5 giây. Mỗi mặt có tối đa 12 giây để nhận diện sau khi ổn định.

| Bước | Nội dung lệnh UART | Mặt chụp | Sửa hướng ảnh |
|---|---|---|---|
| 1 | `RUBIK SCAN_BEGIN` | U tại chỗ | 0° |
| 2 | `RUBIK SCAN_POSE R` | R | 90° thuận chiều |
| 3 | `RUBIK SCAN_POSE F` | F | 0° |
| 4 | `RUBIK SCAN_POSE D` | D | 0° |
| 5 | `RUBIK SCAN_POSE L` | L | 90° ngược chiều |
| 6 | `RUBIK SCAN_POSE B` | B | 180° |
| 7 | `RUBIK SCAN_POSE U` | Trở về mốc | |

Thứ tự chụp là **U → R → F → D → L → B**, thực hiện một lượt trước khi giải.
U đầu tiên được chụp tại chỗ sau SCAN_BEGIN. Sáu lệnh đổi tư thế sau đó là
R, F, D, L, B, U. Chỉ tư thế U cuối cùng bỏ qua chụp.

Mỗi SCAN_POSE vẫn chỉ tư thế tuyệt đối so với Begin, bao gồm hướng của mặt
trong ảnh. Firmware hiện dùng các phép lật quanh hai trục có sẵn và có thể đi
qua tư thế trung gian trong một lệnh. Ví dụ D → L dùng ba lần lật 90°, nhưng
chỉ báo DONE và chụp khi đã tới L. Lộ trình này thay thứ tự thu ảnh, chưa
thay bằng chuỗi servo riêng được tối ưu trên phần cứng khác. Nếu bổ sung
chuỗi servo trực tiếp, cần giữ đúng cả mặt hướng camera và góc ảnh ở bảng trên.

Các chữ U/R/F/D/L/B chỉ vị trí ở thời điểm bắt đầu. Ví dụ nếu tâm đỏ ở trên và tâm xanh biển ở trước, mọi ô đỏ được mã hóa thành U và mọi ô xanh biển thành F trong lượt đó. Pi kiểm tra đủ sáu tâm khác nhau và trạng thái Rubik hợp lệ, rồi kiểm tra công thức trên mô hình. Khi thực thi, mỗi nước đơn gửi dưới dạng `#ID RUBIK MOVE <token>`. Ví dụ `R'` dùng `R_`, và `R2` dùng hai giao dịch riêng. Auto Solve dùng nước đơn để mỗi thao tác kết thúc với các tay kẹp sẵn sàng cho bước sau.

Sau khi quét đủ sáu mặt và trở về U, Pi kiểm tra dữ liệu cube, tìm công thức
và kiểm chứng công thức trên mô hình trước khi gửi chuyển động. App hiển thị
cube, công thức và lệnh UART trong khung kết quả, rồi thực thi từng nước.
Nếu cube ghép theo góc mặc định chưa hợp lệ, Pi dùng cách tìm hướng của Solve
Guide để thử xoay lưới ảnh từng mặt. Pi giữ nguyên màu đã đọc và vị trí mỗi mặt
trong máy. Phiên chỉ tiếp tục nếu tìm được đúng một trạng thái hợp lệ. Nếu
không có trạng thái phù hợp hoặc có nhiều trạng thái, Pi báo lỗi trước khi
gửi nước giải.
Khi mọi lệnh giải đã nhận DONE, phiên kết thúc và báo hoàn thành thực thi.
Kết quả này dựa trên phản hồi STM32. Người dùng quan sát khối thật sau khi chạy.
Nếu khối đã giải từ đầu, app kết thúc sau lượt quét đầu và bỏ qua xoay lớp.

Mỗi lệnh chờ `>#ID OK` rồi `>#ID DONE`. Hạn chờ OK là 1 giây, hạn chờ DONE là 30 giây cho lệnh quét và 15 giây cho từng giao dịch xoay lớp. Khi Stop, ứng dụng ngừng gửi sau thao tác đang chạy. Sau lỗi hoặc Stop, kiểm tra vị trí thật của khối và tay kẹp, rồi đưa máy về tư thế nạp khối trước khi khởi tạo lại. App không tự gửi lại lệnh chuyển động.

Các lệnh quét giữ một cặp tay trên khối trong khi đổi sang cặp kia. Driver servo hiện dựa vào góc đã ra lệnh và thời gian chờ. Trước khi chạy hết chu trình trên máy mới, thử lộ trình với khối đã giải và kiểm tra đúng mặt đến camera, đúng hướng ảnh và việc giữ khối trên cả hai trục. Sau đó thử với khối xáo trộn nhẹ ở nhiều hướng đặt.

Kiểm thử C với servo giả lập từ thư mục gốc:

```text
python firmware/rubik_stm32_ver1/tests/run_command_tests.py --scan-only
```

Bài kiểm thử này phát lại lộ trình UART qua parser thật và kiểm tra lệnh
`#9 RUBIK MOVE F` trả `OK` rồi `DONE`. Nếu Pi gửi đúng lệnh nhưng bo trả
`BAD_ARG`, hãy build và nạp lại firmware từ mã nguồn đang dùng. File ELF
lưu sẵn trong `Debug/` có thể thuộc lần build cũ.

Có thể tạo ELF mới từ thư mục gốc bằng lệnh sau khi đã có `arm-none-eabi-gcc`
trong PATH. Nếu dùng toolchain trong CubeIDE, thêm `--gcc` với đường dẫn đầy đủ
đến chương trình GCC.

```text
python firmware/rubik_stm32_ver1/build_firmware.py --output artifacts/firmware/rubik_stm32_ver1-autosolve.elf
```

Mở file ELF vừa tạo trong STM32CubeProgrammer, kết nối ST-LINK qua SWD rồi
chọn nạp và xác minh bản nạp. Sau khi reset, đóng ứng dụng Auto Solve trên Pi
và thử một lệnh `RUBIK MOVE F` qua terminal UART với cơ cấu đã sẵn sàng xoay.
