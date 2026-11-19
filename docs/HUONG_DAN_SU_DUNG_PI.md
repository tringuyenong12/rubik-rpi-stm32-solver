# Hướng dẫn sử dụng Rubik Solver trên Raspberry Pi

Tài liệu dành cho cấu hình hiện tại: Raspberry Pi, camera USB Logitech C270,
Desktop/VNC đăng nhập bằng tài khoản `pc`, terminal chạy ứng dụng bằng `nguy3n`.
Thư mục dự án: `/home/nguy3n/rubik-rpi-stm32-solver`.

## 1. Mở ứng dụng

1. Bật Pi, cắm camera vào **Pi**, kết nối VNC Viewer và đăng nhập Desktop.
2. Nếu chạy bằng tài khoản `nguy3n` trong khi Desktop dùng `pc`, cấp quyền mở cửa sổ:

```bash
sudo -u pc env DISPLAY=:0 XAUTHORITY=/home/pc/.Xauthority xhost +SI:localuser:nguy3n
```

3. Mở ứng dụng:

```bash
cd ~/rubik-rpi-stm32-solver
DISPLAY=:0 .venv-pi/bin/python -B scripts/run_vision_gui.py --camera 0 --backend auto
```

Cửa sổ `Solver Client` và `Rubik Cube Detection` xuất hiện trên Desktop VNC.
Giữ terminal đang chạy ứng dụng mở.

Trong cùng phiên Desktop, những lần mở tiếp chỉ cần bước 3.
Sau khi khởi động lại hoặc đăng nhập lại Desktop, có thể cần cấp quyền lại.
Không bắt buộc bật tự động đăng nhập; cần có phiên Desktop đang hoạt động.

Các giá trị `pc`, `nguy3n`, `:0` ở trên dành cho cấu hình đã kiểm tra trên Pi này.
Nếu mở Terminal trực tiếp trong Desktop bằng chính tài khoản sở hữu Desktop,
có thể chạy lệnh Python mà không cần bước cấp quyền hay tiền tố `DISPLAY=:0`.

## 2. Quét Rubik và xem hướng dẫn giải

Đây là chế độ cầm Rubik bằng tay, camera nhận diện màu rồi hiển thị công thức.

1. Trong Solver Client, bật **Auto scan** và **Auto solve after 6 faces**.
2. Giữ hostname `localhost`, port `8080`. Có thể dùng solver cục bộ dự phòng
   khi kết nối tới server localhost bị từ chối vì server chưa chạy.
3. Chờ camera ổn định trong **2 giây đầu** (`Camera settling...`).
4. Đưa trọn một mặt gồm 9 ô vào vùng ROI. Dùng ánh sáng đều, tránh bóng tay
   và phản chiếu; giữ camera cố định.
5. Giữ mặt Rubik yên ít nhất **1,2 giây và đủ 10 mẫu hợp lệ**. Thực tế nên
   giữ khoảng 2–3 giây; nếu màu còn thay đổi thì cần giữ lâu hơn.
6. Chỉ chuyển mặt khi thấy thông báo xanh, ví dụ:

```text
DA LUU MAT DO (1/6)
XOAY MAT TIEP - KHONG CAN CHO
```

Thông báo hiện khoảng 2 giây, nhưng **có thể chuyển mặt ngay**, không cần chờ
thông báo tắt hay đếm 5 giây. Mặt sau vẫn phải giữ yên để nhận diện ổn định.

7. Lần lượt quét đủ 6 màu tâm. Không bắt buộc theo thứ tự, nhưng khi quét chỉ
   xoay **cả khối Rubik**, không xoay riêng các tầng làm thay đổi trạng thái.
8. Đủ `6/6`, chương trình kiểm tra trạng thái và tự tìm lời giải. Nếu tắt tự
   giải, bấm **Solve**. Nếu báo sai màu/trạng thái, sửa hoặc quét lại mặt sai.
9. Trong cửa sổ hướng dẫn, bấm **Bước tiếp →**, **← Bước trước** hoặc dùng phím
   mũi tên trái/phải để xem từng bước.

### Hướng cầm khi quét thủ công

| Mặt | Màu tâm | Hướng đặt khi đưa mặt đó về camera |
| --- | --- | --- |
| U | Vàng | Cạnh trên giáp mặt cam |
| D | Trắng | Cạnh trên giáp mặt đỏ |
| F | Đỏ | Cạnh trên giáp mặt vàng |
| R | Xanh lá | Cạnh trên giáp mặt vàng |
| L | Xanh biển | Cạnh trên giáp mặt vàng |
| B | Cam | Cạnh trên giáp mặt vàng |

### Hướng cầm khi làm theo công thức

Giữ **F đỏ về phía bạn, U vàng ở trên, R xanh lá bên phải**.
Đọc chiều xoay khi nhìn thẳng vào chính mặt đang xoay.

| Ký hiệu | Thao tác |
| --- | --- |
| `R`, `L`, `U`, `D`, `F`, `B` | Xoay mặt tương ứng 90° cùng chiều kim đồng hồ |
| Dấu `'`, ví dụ `R'` | Xoay 90° ngược chiều kim đồng hồ |
| Số `2`, ví dụ `R2` | Xoay 180° |

Camera trong chế độ hướng dẫn chỉ quét màu; không xác nhận bạn đã xoay đúng
hay Rubik thực tế đã giải xong. Bạn tự chuyển bước sau mỗi thao tác.

## 3. Các nút thường dùng

| Nút | Cách sử dụng |
| --- | --- |
| Auto scan | Bật/tạm dừng tự động lưu mặt |
| Rescan shown face | Đưa mặt sai về camera rồi bấm để xóa mặt đó và quét lại |
| Rotate saved face 90 | Xoay sơ đồ mặt đã lưu 90°, dùng khi dữ liệu bị sai hướng |
| New scan | Xóa lượt quét và bắt đầu lại |
| Webcam import | Lưu mặt camera hiện tại nếu dữ liệu hợp lệ; tự động quét thường không cần nút này |
| Solve | Kiểm tra dữ liệu và tìm lời giải |
| Xem công thức và hình hướng dẫn | Mở lại cửa sổ hướng dẫn sau khi đã có lời giải |
| Sao chép công thức | Sao chép chuỗi bước giải |
| Lưu hướng dẫn .html | Xuất hướng dẫn và hình minh họa để mở ngoại tuyến |

Để sửa màu thủ công, chọn màu trong bảng màu rồi bấm ô sai trên sơ đồ.
Ô tâm không sửa bằng cách này. Việc sửa sẽ tạm dừng tự động quét;
kiểm tra xong bấm **Solve** hoặc bật lại **Auto scan** nếu cần quét tiếp.

## 4. Căn vùng nhận diện ROI

Bấm vào cửa sổ camera trước khi dùng phím tắt.

- Nhấn **p**, rồi bấm lần lượt bốn góc mặt Rubik theo vòng quanh mặt,
  bắt đầu từ góc trên trái: trên trái → trên phải → dưới phải → dưới trái.
- Giữ cả 9 ô trong vùng đã chọn, không chọn cả nền xung quanh.
- Nhấn **r** để xóa ROI đã chọn và trở về vùng mặc định.
- ROI được lưu theo chỉ số camera trong `calibration/camera_roi.json`.

## 5. Chạy server riêng nếu cần

Chạy ở terminal khác, giữ terminal đó mở:

```bash
cd ~/rubik-rpi-stm32-solver
.venv-pi/bin/python -u -B rpi/twophase/start_server.py 8080 20 3
```

Đợi `Server now listening...`. Lần đầu có thể mất thời gian tạo bảng tra.
Ba tham số là cổng TCP, số nước giải tối đa và thời gian tìm kiếm yêu cầu (giây).
Trong GUI, đặt hostname `localhost`, port `8080`.

Nếu thử server ở cổng `8081`, phải đổi cả port trong GUI sang `8081`.
Server trả lời giải; giao diện quét camera mở trong Desktop, không phải trang web.

## 6. Điều khiển cơ cấu STM32 tự động

Chế độ hướng dẫn ở mục 2 dùng tay xoay Rubik. Muốn máy tự quét và xoay,
dùng khu vực **Auto Solve** với STM32 đã kết nối UART và cơ cấu đã hiệu chỉnh.

1. Đặt Rubik ngay ngắn trong máy, camera nhìn từ trên, thấy trọn 9 ô.
   Với chế độ này, màu tâm hướng lên có thể là bất kỳ màu nào.
2. Chọn đúng cổng UART, baud mặc định `115200` và cấu hình solver.
3. Bấm **Start**. Phần mềm chụp mặt đầu, sau đó kiểm tra UART và yêu cầu
   máy đổi tư thế để chụp các mặt tiếp theo.
4. Theo dõi bộ đếm `6/6`, kết quả kiểm tra, lời giải và các phản hồi hoàn tất.
5. **Stop after current operation** dừng gửi bước tiếp theo sau thao tác hiện tại;
   không phải nút dừng cơ khí tức thì.

Chức năng này cần firmware và cơ cấu thực hiện đúng `SCAN_POSE` và `TURN`,
trả phản hồi hoàn tất tương ứng. Xem chi tiết tại [AUTO_SOLVE.md](AUTO_SOLVE.md),
đặc biệt phần giới hạn tích hợp, trước khi vận hành máy.
Thông báo hoàn tất dựa trên phản hồi của máy, không phải camera quét lại để
xác minh toàn bộ Rubik đã giải xong.

## 7. Xử lý lỗi thường gặp

### `no display name and no $DISPLAY environment variable`

Phiên Desktop phải đang đăng nhập. Với cấu hình hiện tại, chạy lại lệnh cấp
quyền ở mục 1 và dùng đúng tiền tố `DISPLAY=:0` khi mở ứng dụng.
Chỉ cấp quyền bằng `xhost` không tự đặt biến `DISPLAY` cho terminal.

### `Authorization required` hoặc `couldn't connect to display`

Kiểm tra VNC có đang hiển thị Desktop và chạy lại lệnh cấp quyền.
Nếu đổi tài khoản Desktop hoặc số màn hình, cần chỉnh lệnh cho đúng phiên mới.

### `Cannot open camera 0`

Kiểm tra:

```bash
lsusb
v4l2-ctl --list-devices
```

C270 cần xuất hiện trong danh sách cùng thiết bị capture, hiện tại là
`/dev/video0`. Camera phải cắm vào Pi; VNC không chuyển tiếp camera từ máy tính.
Đóng ứng dụng khác đang dùng camera và thử cắm lại USB.
Các thiết bị `bcm2835-codec`, `bcm2835-isp` không phải camera USB để chọn thay.

### Camera có ảnh nhưng chưa lưu mặt

| Dòng trạng thái | Cần làm |
| --- | --- |
| Camera settling | Chờ hết thời gian ổn định ban đầu |
| Looking for all 9 stickers | Căn lại ROI, đưa đủ 9 ô vào ảnh |
| Auto scan paused | Bật Auto scan |
| Hold … still | Giữ nguyên mặt, chờ đủ mẫu ổn định |
| Checking … colors | Tránh rung, bóng và lóa; chờ màu ổn định |
| already saved / turn to a different face | Chuyển sang mặt có màu tâm khác; dùng Rescan shown face nếu muốn quét lại |
| Center uncertain | Đưa mặt mới rõ ràng vào ảnh, tránh để tâm bị lóa hoặc nhận nhầm |

Nếu màu nhấp nháy, chỉnh ánh sáng và vị trí trước khi chỉnh thanh ngưỡng màu.
Đặt lại ROI khi đổi góc camera hoặc khoảng cách.

### `Server socket bind failed`

Giữ lại mã lỗi để chẩn đoán; không phải mọi lỗi bind đều do trùng cổng.
Kiểm tra có server cũ đang chạy không. Có thể thử cổng `8081` rồi đổi GUI theo,
hoặc dùng solver cục bộ dự phòng cho chế độ hướng dẫn thủ công.

## 8. Đóng ứng dụng

Đóng cửa sổ **Solver Client** để kết thúc GUI và giải phóng camera.
Trong cửa sổ camera, **q**, **x** hoặc **Esc** đóng phần camera.
Terminal server riêng có thể dừng bằng **Ctrl+C**.
Nếu đang chạy cơ cấu tự động, dùng quy trình dừng ở mục 6 trước khi đóng GUI.
