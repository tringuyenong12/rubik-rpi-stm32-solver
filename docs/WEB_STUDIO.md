# Hướng dẫn chạy đầy đủ các chức năng

## Chọn ứng dụng cần chạy

| Ứng dụng            | Lệnh từ thư mục gốc                                          | Địa chỉ / đầu ra                             |
| ------------------- | ------------------------------------------------------------ | -------------------------------------------- |
| Web ba chức năng    | `.\.venv\Scripts\python.exe -B scripts\run_web.py`           | `http://127.0.0.1:5000`                      |
| Web 3D + server TCP | `.\.venv\Scripts\python.exe -B rpi\twophase\start_server.py` | `http://127.0.0.1:8080`                      |
| GUI webcam desktop  | `.\.venv\Scripts\python.exe -B scripts\run_vision_gui.py`    | Cửa sổ Tkinter/OpenCV; Solve cần server 8080 |
| Demo pipeline       | `.\.venv\Scripts\python.exe -B scripts\demo_pipeline.py`     | Terminal                                     |

Các API ở cổng 5000 và 8080 khác nhau; không thay cổng trong ví dụ nếu chưa chọn đúng ứng dụng. Hai server có thể chạy đồng thời, nhưng chỉ một chương trình nên giữ camera Logitech tại một thời điểm.

## Chạy trên Windows

Tại thư mục gốc, tạo môi trường nếu chưa có rồi cài thư viện:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r rpi\requirements.txt
.\.venv\Scripts\python.exe -B scripts\run_web.py --camera 1 --backend dshow --port 5000
```

Mở http://127.0.0.1:5000. Không cần Node.js, build frontend hoặc server solver riêng. Nút **Mở camera** mới mở thiết bị. Đóng chương trình Camera/GUI cũ trước để nhả Logitech.

Trên Raspberry Pi, chọn ID và backend thực tế, ví dụ:

```bash
python scripts/run_web.py --camera 0 --backend v4l2
```

Web 3D/TCP cũ vẫn được giữ nguyên. Rubik Studio chạy riêng; API mới không thay API cũ ở cổng 8080.

## 1. Hướng dẫn qua camera

Chức năng này nằm trong đúng hai file:

- `rpi/rubik_robot/web/camera_tutorial.py`: toàn bộ phát hiện mặt, quét, gọi solver và điều phối từng nước; kèm bộ chuyển ảnh/trạng thái lên web.
- `rpi/rubik_robot/web/tutorial_moves.py`: đủ 16 hàm xoay mặt 3×3, xoay sáu mặt, đổi hướng nhìn khối, vẽ mũi tên và xác nhận màu.

Các file HTTP/giao diện chỉ gọi bắt đầu/dừng và hiển thị kết quả. Không dùng bộ hướng dẫn rút gọn trong `cube.py`/`service.py`.

1. Chọn **Hướng dẫn giải**, chọn camera ID/backend trong **Thiết lập camera** nếu cần.
2. Bấm **Bắt đầu quét & hướng dẫn**. Không cần quét thủ công trước, chọn ROI hay calibration LAB cho chức năng 1.
3. Đưa mặt F ra camera, tiếp theo U → D → R → L → B khi có lời nhắc. Chương trình tự ghi mỗi mặt sau bỏ phiếu 5 mẫu hợp lệ và có các khoảng chờ chuyển mặt.
4. Đưa lại mặt F khi được nhắc. Bộ giải tạo chuỗi nước; giữ hệ mặt theo sáu tâm đã chọn lúc quét.
5. Làm theo các mũi tên vẽ trực tiếp trong ảnh. Mỗi thao tác được so màu bằng 10 mẫu. Nước 180° gồm hai lần 90° có xác nhận riêng; nước B đổi sang hướng nhìn phải, xoay, rồi trở lại mặt trước.
6. Khi hiện CUBE SOLVED/CUBE ALREADY SOLVED, kiểm tra sáu mặt thật. Bấm **Dừng hướng dẫn** để huỷ và nhả camera.

Giữ mặt gần vuông góc và ánh sáng đều. Bộ phát hiện giữ ngưỡng diện tích sticker 1000–3000 pixel², tương đương cạnh khoảng 32–55 pixel trên ảnh 640×480; cần điều chỉnh khoảng cách cube. Nếu sai màu/trạng thái, chương trình trở lại quét. Các ngưỡng BGR và công thức mũi tên được giữ; không thay bằng LAB trong chức năng này.

Web nhận ảnh đã vẽ đường bao/mũi tên, không dùng mũi tên giả lập từ sơ đồ. Không tự tạo video AVI. Lớp tương thích giữ kết quả mode ở dạng 1×9, chuyển tọa độ mũi tên sang số nguyên cho OpenCV và bổ sung các import cần thiết. Nhánh cube đã giải kết thúc trước vòng điều phối để tránh biến lời giải chưa khởi tạo.

API: `POST /api/tutorial/start` với `{"index":1,"backend":"dshow"}`, `POST /api/tutorial/stop` với `{}`, `GET /api/status` có trường `tutorial`, ảnh ở `GET /api/tutorial/frame.jpg`. Các thao tác cần camera khác bị chặn khi hướng dẫn còn giữ thiết bị.

## 2. Bộ đề từ cube hoàn chỉnh

- Dễ: 5 nước; trung bình: 12; khó: 22.
- Không chọn liên tiếp hai mặt cùng trục, tránh các bước triệt tiêu dư thừa đơn giản.
- Seed cho phép tạo lại cùng chuỗi trộn.
- Mức độ là độ dài chuỗi tạo đề, không khẳng định độ sâu tối ưu hoặc độ khó đối với người chơi.
- Đầu ra gồm chuỗi trộn, trạng thái đích, chuỗi giải Two-Phase, chuỗi nghịch đảo và hai bộ lệnh UART riêng.
- Tải **TRỘN.txt** để đưa từ cube hoàn chỉnh tới đề; **GIẢI.txt** để đưa đề về hoàn chỉnh; JSON giữ cả bộ đề.

Mỗi lời giải được áp lại lên mô hình cubie, phải về SOLVED trước khi xuất. Không có giao tiếp PCA9685 hoặc điều khiển servo trong web mới.

## 3. Quét tự động với camera top-down

Chức năng 3 dùng bộ nhận màu và kế hoạch quét riêng; không lấy chức năng hướng dẫn để vận hành robot:

1. Dừng hướng dẫn trước, chọn **Giải tự động**, mở camera.
2. Mở phần thiết lập, chọn bốn góc mặt theo thứ tự trái-trên → phải-trên → phải-dưới → trái-dưới.
3. Đưa lần lượt sáu sticker tâm vào ô giữa và lấy mẫu tương ứng: U trắng, R đỏ, F xanh lá, D vàng, L cam, B xanh biển.
4. Mẫu LAB lưu ở `calibration/web_color_profile.json`. Camera thật yêu cầu đủ sáu mẫu; ảnh phải ổn định tám khung và đủ độ tin cậy/độ nét mới được ghi.

**Khung cố định** lấy mẫu giữa sticker để tránh viền đen. **Đường bao sticker** tự tìm chín ô. Khi chưa đủ mẫu tâm, giao diện báo đang dùng ngưỡng BGR; không bắt đầu lượt quét thật cho tới khi đủ calibration.

Hệ trục cố định: +X hướng R, +Y hướng U, +Z hướng F. Camera nhìn xuống +Y; trên ảnh hướng B, bên phải ảnh hướng R. Không phản chiếu ảnh. Tư thế ban đầu U ở trên, F hướng người vận hành, R bên phải.

`X +1` xoay **cả khối** 90° theo chiều nước R: F lên U. `Z +1` theo chiều nước F: L lên U. Góc được tính khi nhìn trực diện phía dương của trục tương ứng. `-1` là chiều ngược, `2` là 180°.

| Thứ tự | Thao tác      | Mặt dưới camera   |
| -----: | ------------- | ----------------- |
|      1 | Chụp          | U                 |
|      2 | REORIENT X 1  | F                 |
|      3 | REORIENT X 1  | D                 |
|      4 | REORIENT X 1  | B                 |
|      5 | REORIENT X 1  | U, không chụp lại |
|      6 | REORIENT Z -1 | R                 |
|      7 | REORIENT Z 2  | L                 |
|      8 | REORIENT Z -1 | Trả về tư thế gốc |

Web tự xoay thứ tự sticker của ảnh về hệ URFDLB. Ảnh B cần đảo 180°; R/L cần đổi thứ tự hàng/cột theo pose. Sau DONE cuối mới lắp 54 sticker, kiểm tra số lượng/hướng/parity, gọi Two-Phase và xuất lệnh giải. Không dùng nước xoay một mặt để thay cho lật cả khối: làm vậy sẽ thay đổi trạng thái đang quét.

Ba cách thử:

- **Mô phỏng:** tự chạy ACK/ảnh giả từ trạng thái hợp lệ, không camera hay UART. Dùng kiểm tra phần mềm.
- **Tự đổi tư thế:** camera thật; người vận hành lật khối đúng lệnh rồi bấm DONE. Web tự chụp khi ổn định.
- **Bộ UART ngoài:** API cung cấp lệnh đang chờ; phần giao tiếp của người dùng gửi tới controller và POST DONE đúng ID. Web không tự mở COM hoặc giả định servo đã chạy.

Cần cơ khí lật cả khối quanh trục ngang X và trục Z (hoặc chuỗi tương đương). Chỉ quay bàn quanh trục đứng không đưa đủ sáu mặt lên camera. Tài liệu cơ khí hiện tại chưa chốt mapping/pulse, nên kế hoạch này là hợp đồng tư thế, không phải sequence servo đã đo. Firmware hiện tại chưa hỗ trợ REORIENT; không gửi nguyên lệnh này rồi giả định robot cũ tự hiểu.

## Hợp đồng bàn giao UART

Lệnh trộn/giải giữ định dạng cũ, mỗi dòng có newline:

```text
TURN R 1 450
TURN U -1 450
TURN F 2 900
```

Lệnh đổi tư thế mới, cùng quy ước quarter-turn và thời gian ước lượng:

```text
REORIENT X 1 800
REORIENT Z -1 800
REORIENT Z 2 1600
```

`CAPTURE` trong kế hoạch là tác vụ host, không gửi tới servo. ID trong JSON dùng để chống ACK cũ. Khi đã thực hiện đúng chuyển động, bridge trả:

```http
POST /api/scan/ack
Content-Type: application/json

{"id": 2, "result": "DONE"}
```

`OK` không đủ. Không ACK khi cơ khí thất bại. Lấy lệnh đang chờ từ `GET /api/scan`, trường `scan.next`. GET có thể lặp lại cùng ID: bridge phải chống gửi lặp. Khi huỷ giữa chừng, phần mềm không tự trả tư thế về gốc; đặt lại trước lượt quét mới.

## 4. Web 3D và GUI desktop

### Server web 3D/TCP

```powershell
.\.venv\Scripts\python.exe -B rpi\twophase\start_server.py
```

Mở `http://127.0.0.1:8080`. Thử xoay thủ công, tạo trạng thái trộn và chạy giải ở chế độ **simulated**. Các nút pause/resume/step/stop điều khiển tiến trình mô phỏng; danh sách actuator là trạng thái phần mềm, không phải cảm biến servo thật.

Có thể chọn cổng khác:

```powershell
.\.venv\Scripts\python.exe -B rpi\twophase\start_server.py 8081 20 3
```

Khi đó mở `http://127.0.0.1:8081` và đổi Port trong GUI desktop sang 8081. Không chạy hai server trên cùng cổng.

Test API 3D, không dùng phần cứng:

```powershell
$web3d = 'http://127.0.0.1:8080'
Invoke-RestMethod "$web3d/api/reset" -Method Post -ContentType 'application/json' -Body '{}'
Invoke-RestMethod "$web3d/api/move" -Method Post -ContentType 'application/json' -Body '{"move":"R"}'
Invoke-RestMethod "$web3d/api/solve" -Method Post -ContentType 'application/json' -Body '{"mode":"simulated","duration_ms":100}'
Invoke-RestMethod "$web3d/api/status"
```

### GUI desktop

Để server 8080 chạy ở terminal thứ nhất. Terminal thứ hai:

```powershell
.\.venv\Scripts\python.exe -B scripts\run_vision_gui.py
```

GUI dùng Hostname `localhost`, Port `8080`. Chọn màu và click sticker để tô tay; Webcam import ghi một mặt; Clean tạo cube hoàn chỉnh; Empty xoá các ô không phải tâm; Scramble mở các mức trộn. Solve gọi server và hiển thị lời giải.

Bộ màu mặc định GUI desktop **khác web ba chức năng**:

| Mặt | GUI desktop | Web ba chức năng |
| --- | ----------- | ---------------- |
| U   | Vàng        | Trắng            |
| R   | Xanh lá     | Đỏ               |
| F   | Đỏ          | Xanh lá          |
| D   | Trắng       | Vàng             |
| L   | Xanh biển   | Cam              |
| B   | Cam         | Xanh biển        |

GUI desktop mặc định mở camera 0. Để dùng Logitech camera 1/DirectShow mà không sửa file:

```powershell
@'
import cv2
import runpy

capture_device = cv2.VideoCapture
cv2.VideoCapture = lambda index, *args, **kwargs: capture_device(1, cv2.CAP_DSHOW)
runpy.run_path("scripts/run_vision_gui.py", run_name="__main__")
'@ | .\.venv\Scripts\python.exe -B -
```

Các byte xoay được GUI desktop liệt kê chỉ là dữ liệu hiển thị. Web ba chức năng xuất lệnh ASCII TURN; phải dùng đúng định dạng mà firmware đích nhận, không trộn hai định dạng với nhau.

## 5. CLI: demo, giải cube và in lệnh

```powershell
.\.venv\Scripts\python.exe -B scripts\demo_pipeline.py

Push-Location rpi
..\.venv\Scripts\python.exe -B -m rubik_robot.main --help
..\.venv\Scripts\python.exe -B -m rubik_robot.main --mode solve --cube "DUUBULDBFRBFRRULLLBRDFFFBLURDBFDFDRFRULBLUFDURRBLBDUDL" --duration-ms 450 --face-turn-command TURN
Pop-Location
```

Kết quả gồm cube string, lời giải và các dòng TURN. `--mode demo` và `--mode solve` đều in kết quả; không gửi UART. Đổi `--face-turn-command MOVE` để xuất tên lệnh cũ. Thời lượng của nước 180° gấp đôi nước 90°.

Demo pipeline sử dụng cube hoàn chỉnh: `already solved` và `actions: []` là bình thường. Các dòng `loading ... table` là nạp bảng của solver.

## 6. UART và firmware

### Kiểm tra kết nối, chưa chạy chuyển động

```powershell
.\.venv\Scripts\python.exe -B -m serial.tools.list_ports
.\.venv\Scripts\python.exe -B -m serial.tools.miniterm COM5 115200 --eol LF --echo
```

Thay COM5 bằng cổng thực tế. Gửi `PING`, chờ `OK PONG`; thoát terminal serial bằng `Ctrl+]`.

### Chế độ gửi lệnh CLI

Lệnh sau **thực sự mở serial và gửi PING/HOME**, kể cả khi cube mặc định đã giải:

```powershell
Push-Location rpi
..\.venv\Scripts\python.exe -B -m rubik_robot.main --mode send --port COM5 --baudrate 115200
Pop-Location
```

Chỉ dùng sau khi đã nạp firmware, cấu hình profile và kiểm tra cơ khí. Thêm `--cube` để gửi lời giải của trạng thái khác. Lớp serial CLI hiện đọc một dòng phản hồi/request; cần kiểm chứng việc xử lý OK/DONE trước khi dùng chuỗi chuyển động thật.

Firmware trong project cung cấp thư viện và snippet cho CubeIDE. Phải cấu hình timer/UART và điền profile PWM trước khi Start. Các sequence TURN/MOVE/SCAN_POSE chưa triển khai, REORIENT chưa được firmware hỗ trợ. STOP khoá lệnh mới và giữ PWM cuối; không cắt nguồn servo. PCA9685 không được điều khiển bởi web.

Các hướng dẫn nội bộ liên quan: [CubeIDE](CUBEIDE_SETUP.md), [UART](UART_PROTOCOL.md), [profile servo](../firmware/stm32cubeide/App/SERVO_CONTROLLER_GUIDE.md).

## 7. Test bằng terminal

Từ thư mục gốc, chạy toàn bộ test cũ và mới:

```powershell
Push-Location rpi
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
Pop-Location
```

Trong terminal thứ hai khi web đang chạy, test bộ đề:

```powershell
$task = Invoke-RestMethod http://127.0.0.1:5000/api/scramble -Method Post -ContentType 'application/json' -Body '{"level":"hard","seed":42}'
$task.scramble
$task.scramble_uart
$task.solution.uart
```

Test full lượt quét mô phỏng, không mở camera hay UART:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/clear -Method Post -ContentType 'application/json' -Body '{}'
Invoke-RestMethod http://127.0.0.1:5000/api/scan/start -Method Post -ContentType 'application/json' -Body '{"mode":"demo"}'
1..13 | ForEach-Object { Invoke-RestMethod http://127.0.0.1:5000/api/scan/demo-step -Method Post -ContentType 'application/json' -Body '{}' | Select-Object status,index }
$result = Invoke-RestMethod http://127.0.0.1:5000/api/status
$result.scan.solution.uart
```

Các test bao phủ đổi tư thế/chiều ảnh với mặt không đồng màu, đủ sáu mặt, trở về pose gốc, ACK sai ID, từ chối OK, cube vô nghiệm, xác nhận hướng dẫn bằng ảnh đúng/sai, ba mức đề và API HTTP. Dữ liệu màu tổng hợp không thay thế kiểm thử ánh sáng/Logitech/robot thật.

Test riêng phần web ba chức năng:

```powershell
Push-Location rpi
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_web_workflows.py -v
Pop-Location
```

Test driver servo bằng HAL giả, cần GCC hoặc biến CC:

```powershell
.\.venv\Scripts\python.exe -B firmware\tests\run_tests.py
```

## 8. Xử lý lỗi và dừng ứng dụng

| Hiện tượng                       | Cách kiểm tra                                                                           |
| -------------------------------- | --------------------------------------------------------------------------------------- |
| Không mở được camera             | Đóng ứng dụng giữ camera, chọn đúng ID; Logitech trên máy hiện tại dùng ID 1/DirectShow |
| Có hình nhưng không ghi được mặt | Căn lại bốn góc, giảm phản chiếu, lấy đủ mẫu tâm và chờ ổn định 8 khung hình            |
| Nhầm đỏ/cam hoặc trắng/vàng      | Lấy lại sáu mẫu tâm trong cùng ánh sáng                                                 |
| Tâm trùng mặt trước              | Kiểm tra đã lật cả khối đúng tư thế chưa; không ghi lại cùng mặt                        |
| Cube báo flip/twist/parity       | Kiểm tra màu và hướng hàng/cột của sáu mặt                                              |
| Quét dừng ở waiting_done         | Bộ ngoài chưa gửi DONE đúng ID; OK không đủ                                             |
| Cổng đang sử dụng                | Dừng server trùng hoặc chọn cổng khác, cập nhật địa chỉ tương ứng                       |
| GUI Solve không kết nối          | Kiểm tra server 8080, Hostname/Port của GUI                                             |
| ERR CONFIG                       | Firmware thiếu/sai profile hoặc PWM chưa khởi động                                      |
| ERR UNSUPPORTED                  | Firmware chưa có sequence cho lệnh đó                                                   |

Bấm **Đóng camera** để nhả thiết bị; dùng `Ctrl+C` ở terminal để dừng server. Huỷ quét giữa chừng không tự đưa cube về tư thế gốc. Sau khi cập nhật web, khởi động lại server và dùng `Ctrl+F5` để nạp giao diện mới.
