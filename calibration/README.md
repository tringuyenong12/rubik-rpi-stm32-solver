# Calibration Data

Thư mục này dùng để lưu file calibration thực tế, ví dụ:

- `color_profile.json`: màu center, grid sticker, thông số camera.
- `servo_profile.json`: góc/pulse an toàn từng servo.

Các file `.json` mới trong thư mục này được ignore; các profile camera đã được track vẫn được Git theo dõi.

Camera C270 trên Linux (camera 0) đã đo lại ngày 18/11/2026 với ánh sáng tại máy:
cân bằng trắng thủ công **6000 K**, exposure **60**, gain **0**. Cấu hình cũ
3500 K làm ô trắng ám xanh, saturation khoảng 68–71 và bị nhận thành blue.
Ở 6000 K, saturation trắng khoảng 7–10, còn xanh dương khoảng 193–201.
Thông số nằm trong `camera_settings.json`, ở cả `capture_by_platform.linux`
và `v4l2_controls`; cần đo lại nếu đổi đèn hoặc vị trí camera.

ROI bốn góc nằm trong `camera_roi.json`, theo thứ tự trên-trái, trên-phải,
dưới-phải, dưới-trái của mặt cần quét. Với mặt đặt hình thoi, chọn đỉnh trên,
phải, dưới, trái. Chương trình tự sửa chiều chọn góc ngược để lưới không bị
phản chiếu. Khi thay ROI, quét lại các mặt đã lưu theo ROI cũ.

## Kiểm tra lại đỏ/cam và xanh/trắng trên C270

Với ánh sáng và cơ cấu ngày 2026-11-18, camera 0 dùng `orange_L=9`:
vùng phản sáng trên ô đỏ đo H khoảng 7–8, trong khi ô cam đo H khoảng 10–11.
Giữ `sat_W=35`, WB 6000 K, exposure 60 và gain 0.
ROI tại ảnh 640×480 là `(291,75), (463,249), (291,415), (117,245)`.
Thông số này cần đo lại nếu đổi ánh sáng hoặc vị trí máy.

Kiểm tra ổn định dùng HSV ở vùng giữa cố định của mỗi ô, tách khỏi số đo
phân loại có thể chuyển sang viền ô để tránh lóa. Nhờ đó việc chuyển vùng
lấy mẫu không tự đặt lại bộ đếm giữ mặt. Màu còn mơ hồ vẫn bị chặn lưu.

Ảnh gốc, cấu hình sao lưu và kết quả kiểm thử nằm ở `artifacts/color_recheck/`.
`replay_three_faces.py` kiểm thử các mặt tâm xanh, vàng, đỏ qua ba vòng và
kiểm tra cả số tín hiệu lưu thành công; xem `three_face_replay.json`.
