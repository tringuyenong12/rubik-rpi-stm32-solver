# Auto Solve — camera trên cao và UART

Tab `Auto Solve` chạy trên cùng Solver Client với `Solve Guide` và `Scramble`.
Thuật toán và dữ liệu của hai tính năng trước được giữ nguyên. Tab mới sở hữu
camera, sơ đồ màu, kết nối UART và phiên giải riêng.

## Chạy

Từ thư mục gốc project, mở server ở terminal thứ nhất.

```powershell
.\.venv\Scripts\python.exe -B rpi\twophase\start_server.py 8080 20 3
```

Mở client ở terminal thứ hai.

```powershell
.\.venv\Scripts\python.exe -B scripts\run_vision_gui.py --camera 1 --backend dshow
```

1. Chọn `Auto Solve`.
2. Đặt Rubik đã xáo trộn vào máy với **bất kỳ màu tâm nào hướng lên camera**.
   Khối cần nằm ngay ngắn trong máy. Hướng màu phía trước và bên phải tùy ý.
3. Căn camera sao cho cạnh trên ảnh hướng về phía sau máy, cạnh phải ảnh
   hướng về bên phải máy. Dùng ảnh không lật gương, thấy trọn chín ô và đủ sáng.
4. Chọn cổng UART, mặc định 115200 baud. Solver mặc định `localhost:8080`.
5. Bấm `Start` một lần. Chương trình mở Logitech theo lựa chọn khi mở client,
   nhận diện và hiển thị mặt đầu tiên ngay tại chỗ. Sau khi lưu mặt đầu tiên,
   chương trình mới mở UART, kiểm tra PING rồi gửi chuỗi đổi tư thế cố định.
6. Mỗi mặt chụp xong xuất hiện trên sơ đồ, bộ đếm tăng từ `0/6` tới `6/6`.
7. Sau sáu mặt và phục hồi tư thế ban đầu, hiện `6/6 faces captured`,
   kiểm tra trạng thái rồi gọi server Two-Phase.
8. Lời giải và toàn bộ lệnh `TURN` được ghi vào khung kết quả trước khi gửi.
   Có thể dùng `Copy solution UART` hoặc `Save solution .txt`.
9. Từng bước chờ xác nhận hoàn tất. Cuối cùng hiện `AUTO SOLVE COMPLETE`.

Thông báo hoàn tất dựa trên các phản hồi `DONE` của máy. Sơ đồ trong giai đoạn
giải là trạng thái dự đoán sau từng lệnh đã xác nhận, không phải một lượt quét
camera xác minh lại toàn bộ Rubik sau giải.

## Hướng đặt tùy ý và hệ tọa độ máy

U/D chỉ vị trí trên/dưới của Rubik tại thời điểm Start; F/B chỉ trước/sau,
R/L chỉ phải/trái. Màu tâm được phát hiện từ ảnh và gắn vào các vị trí này.
Ví dụ U có thể là đỏ, F có thể là xanh biển. Sơ đồ hiển thị màu thực tế theo
vị trí trong máy và nhật ký ghi rõ `U=red`, `F=blue` khi nhận diện được.

Mỗi lần chụp lưu theo màu tâm và từ chối lưu trùng. Nếu máy chưa đổi sang mặt
mới, camera tiếp tục chờ thay vì ghi đè mặt cũ. Mỗi phiên phải có đủ sáu màu tâm.

Khi đủ sáu mặt, chương trình đổi các nhãn màu sang U/R/F/D/L/B theo **vị trí
thực tế trong máy**. Server giải trạng thái trong hệ tọa độ này. Vì vậy `TURN R`
xoay mặt ở bên phải máy lúc bắt đầu, bất kể màu tâm mặt đó. Sơ đồ tiếp tục dùng
màu thật sau mỗi bước giải đã xác nhận.

## Hợp đồng tư thế chụp cố định

UART đã có lệnh `SCAN_POSE <face>`. **Đây là tư thế tuyệt đối của toàn khối,
tương đối với cách đặt lúc Start**, giữ nguyên trạng thái sticker. Tên vị trí
trong lệnh được xác định theo máy. Firmware cần đưa phía được chỉ định lên
camera theo các phép xoay ở bảng dưới. `SCAN_POSE U` khôi phục cả hướng nghiêng
lẫn hướng quanh trục đứng về cách đặt ban đầu.

Quy ước trục theo tư thế ban đầu: +X hướng R, +Y hướng U, +Z hướng F.
`x` là xoay cả khối -90° quanh +X; `z` là xoay cả khối -90° quanh +Z,
theo quy tắc bàn tay phải. Dấu `'` đảo chiều; số `2` là 180°.
Đây là quy ước hình học để ánh xạ firmware, không phải cú pháp UART mới.

| Bước | UART | Xoay cả khối từ bước trước | Tư thế tuyệt đối | Thao tác camera | Sửa ảnh về chuẩn |
| --- | --- | --- | --- | --- | --- |
| 1 | chụp tại chỗ, chưa gửi UART | giữ nguyên | ban đầu | chụp U, nhận màu tâm bất kỳ | 0° |
| 2 | `SCAN_POSE F` | `x` | `x` | chụp F | 0° |
| 3 | `SCAN_POSE D` | `x` | `x2` | chụp D | 0° |
| 4 | `SCAN_POSE B` | `x` | `x'` | chụp B | 180° |
| 5 | `SCAN_POSE U` | `x` | ban đầu | không chụp | — |
| 6 | `SCAN_POSE R` | `z'` | `z'` | chụp R | 90° thuận chiều |
| 7 | `SCAN_POSE L` | `z2` | `z` | chụp L | 90° ngược chiều |
| 8 | `SCAN_POSE U` | `z'` | ban đầu | không chụp | — |

Thứ tự vị trí được chụp là **U → F → D → B → R → L**.
Chuỗi UART sau lần chụp đầu gồm **F → D → B → U → R → L → U**, giống nhau
cho mọi hướng màu được đặt vào máy.
Camera chờ 0,4 giây cho ảnh ổn định rồi lấy tối thiểu năm mẫu
với thời gian quan sát tối thiểu 0,25 giây, chấp nhận màu tâm mới bất kỳ. Hết 12 giây
không lấy được mặt sẽ dừng và báo lý do. Camera đọc liên tục để loại khung cũ
trong thời gian máy đổi tư thế. Sơ đồ camera được xoay về chuẩn URFDLB ở phía PC.

`Copy scan route` sao chép bảy lệnh tư thế sau lần chụp đầu tiên. Nếu dùng danh
sách đó với chương trình khác, chương trình đó phải chụp mặt đầu tại chỗ rồi
chèn việc chụp và chờ hoàn tất tại các bước trong bảng. Gửi liên tiếp cả danh
sách qua terminal không tự tạo ra sáu ảnh.

## Phản hồi và giới hạn tích hợp

```text
PC:     PING
STM32:  OK PONG

PC:     SCAN_POSE F
STM32:  OK SCAN_POSE
STM32:  DONE SCAN_POSE

PC:     TURN R -1 450
STM32:  OK TURN
STM32:  DONE TURN
```

PC chụp mặt đầu tiên trước khi mở UART. Các mặt còn lại được chụp sau
`DONE SCAN_POSE`. Mỗi bước giải tiếp theo được gửi sau `DONE TURN`.
Mỗi lệnh có hạn chờ 15 giây. Lỗi `ERR`, mất camera, trạng thái không hợp lệ
hoặc timeout sẽ dừng phiên. Không tự gửi lại lệnh vì có thể xoay hai lần.
`Stop after current operation` ngừng các bước tiếp theo sau thao tác đang chạy.
Đóng cửa sổ khi đang chạy cũng chờ thao tác và đóng các kết nối trước.

Firmware hiện tại vẫn có đường trả `ERR UNSUPPORTED` cho thao tác cơ khí chưa
triển khai. Muốn máy xoay thật, firmware cần thực hiện đúng sáu tư thế tuyệt đối
ở bảng trên và các lệnh `TURN`, rồi trả `DONE` sau khi chuyển động kết thúc.
Phần Auto Solve này không bổ sung code servo, PCA9685 hoặc sequence cơ khí STM32.

Sau lỗi hoặc dừng giữa chừng, kiểm tra máy và đưa cơ cấu về tư thế sẵn sàng đặt
khối trước khi bấm Start lại. Rubik có thể có trạng thái xáo trộn và hướng màu
bất kỳ. Start mới lấy cách đặt hiện tại làm mốc cho phiên mới.

## Kiểm thử phần mềm

```powershell
Push-Location rpi
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_auto_solve.py -v
..\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
Pop-Location
```

Các kiểm thử dùng ảnh tổng hợp, phản hồi UART giả lập và trạng thái Rubik biết
trước. Chúng kiểm tra cả 24 hướng đặt của khối, hình học sáu tư thế, chụp mặt đầu
trước UART, chống lưu trùng, phục hồi tư thế, kiểm tra lời giải trong hệ tọa độ
máy, chờ DONE, hủy phiên và ba tab độc lập. Chạy robot với Logitech và cơ khí
thật cần được kiểm tra riêng sau khi firmware đáp ứng hợp đồng tư thế.
