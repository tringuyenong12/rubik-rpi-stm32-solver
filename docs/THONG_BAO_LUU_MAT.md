# Tín hiệu đã lưu mặt Rubik cho chương trình điều khiển

## Mục đích

Sau khi nhận diện ổn định và lưu thành công một mặt, chương trình điều khiển
nhận `True` để tiến hành đổi mặt. Không cần đếm 5 giây hay đọc chữ trên ảnh.
Đây là tín hiệu trong Python, chưa phải tín hiệu điện GPIO hay bản tin UART.

## Đọc tín hiệu

Trong cùng tiến trình Python đang chạy camera, dùng đúng đối tượng scanner:

```python
from rubik_robot.vision.face_scanner import scanner

face_saved = scanner.consume_face_saved()
```

- `True`: có một mặt vừa lưu; tín hiệu đó đã được lấy ra.
- `False`: chưa có mặt mới được lưu kể từ lần lấy tín hiệu trước.
- Mỗi lần lưu tạo một tín hiệu. Tín hiệu được giữ tới khi đọc, không mất chỉ
  vì camera đã xử lý thêm khung hình.
- Chỉ một bộ điều khiển nên đọc hàm này, vì đọc sẽ lấy tín hiệu khỏi hàng đợi.
- Sửa màu hoặc xoay sơ đồ đã lưu không tạo tín hiệu mới.
- Reset lượt quét xóa tín hiệu đang chờ. Quên một mặt để quét lại cũng xóa
  tín hiệu đang chờ của mặt đó; lưu lại mặt đó sẽ tạo tín hiệu mới.

Chạy một script Python riêng sẽ tạo scanner riêng, không nhận được tín hiệu
của GUI. Nếu bộ điều khiển chạy ở tiến trình khác hoặc trên STM32, cần nối
thêm kênh giao tiếp như UART, socket hoặc GPIO.

## Luồng đổi mặt tự động

```text
Chờ nhận diện và lưu mặt
        ↓ consume_face_saved() == True
Đủ 6 mặt? ── Có → dừng đổi mặt, kiểm tra dữ liệu và tìm lời giải
        ↓ Chưa
Tạm dừng tự lưu → gửi lệnh đổi tư thế
        ↓
Chờ cơ cấu báo hoàn tất chuyển động
        ↓
Bật lại tự lưu → nhận diện mặt mới
```

Khi triển khai bộ điều khiển, chỉ gửi một lệnh đổi mặt cho mỗi tín hiệu.
Tạm dừng scanner bằng `scanner.set_enabled(False)` trước khi chuyển động,
và bật lại bằng `scanner.set_enabled(True)` sau khi nhận phản hồi hoàn tất.
Camera vẫn nên đọc khung hình trong lúc chuyển động để tránh dùng ảnh cũ.
Không bật lại nếu cơ cấu báo lỗi hoặc chưa xác nhận hoàn tất.
Luồng điều khiển nên chạy nền để không chặn vòng đọc camera hay giao diện.

Tín hiệu không tự phát lệnh chuyển động: phần gửi lệnh và chờ hoàn tất cần
được nối với bộ điều khiển cơ cấu cụ thể. Chế độ Auto Solve có luồng điều
khiển riêng, xem [AUTO_SOLVE.md](AUTO_SOLVE.md).

## Nếu đang viết trực tiếp vòng xử lý ảnh

`FaceScanner.update(...)` cũng trả về boolean:

```python
saved_now = scanner.update(grid, hsv_grid=hsv_grid, displayed_grid=preview_colors)
if saved_now:
    # Mặt được lưu tại chính lần update này.
    # Báo cho bộ điều khiển bắt đầu quy trình chuyển mặt.
    pass
```

Dùng giá trị trả về này hoặc `consume_face_saved()` làm nguồn kích hoạt,
không dùng đồng thời cả hai để phát hai lệnh cho cùng một mặt.
Không gọi update lần nữa chỉ để kiểm tra tín hiệu nếu vòng camera đã gọi nó.

## Thời gian ổn định

Tín hiệu chỉ thành True sau khi mặt thực sự được lưu. Điều kiện kiểm tra
ổn định vẫn giữ nguyên: tối thiểu 1,2 giây và 10 mẫu hợp lệ trong cấu hình
camera hiện tại. Không có khoảng chờ thêm sau khi lưu để đổi mặt.
Nhận đủ 6 mặt chưa đồng nghĩa trạng thái Rubik đã hợp lệ; vẫn cần kiểm tra.
