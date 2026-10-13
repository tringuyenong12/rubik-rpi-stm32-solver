# Pipeline Thị Giác Máy Tính

## Thứ Tự Scan

Dùng quy ước solver `URFDLB`:

- U: Up
- R: Right
- F: Front
- D: Down
- L: Left
- B: Back

Khi chụp 6 mặt, cần có jig/cách đặt cube có lặp lại để không nhầm hướng. Nếu dùng robot để xoay cube trong lúc scan, mỗi thao tác scan nên được log lại.

## Pipeline Đề Xuất

1. Capture ảnh.
2. Cân bằng trắng hoặc khóa exposure của camera.
3. Tìm vùng Rubik:
   - Theo bản vẽ hiện tại, camera được gắn cố định trên cao nên ưu tiên dùng grid cố định.
   - Thêm bước kiểm tra tâm cube vì các cụm actuator có thể che một phần viền cube.
   - Nâng cao: detect contour/ArUco/reference frame trên jig trung tâm.
4. Lấy mẫu vùng trung tâm của 9 sticker.
5. Chuyển màu sang LAB hoặc HSV.
6. Dùng 6 center stickers làm màu tham chiếu mỗi lần scan.
7. Gán mỗi sticker vào màu center gần nhất.
8. Kiểm tra mỗi màu có đúng 9 stickers.
9. Xuất cube string và ảnh debug overlay.

## Calibration

Nên lưu file `calibration/color_profile.json` gồm:

- Điều kiện ánh sáng.
- Camera id/resolution.
- Vị trí 9 ô trên ảnh.
- Màu center trung bình.
- Threshold khoảng cách màu.

## Debug Bắt Buộc

Mỗi lần scan nên lưu:

- Ảnh gốc.
- Ảnh overlay đánh dấu 9 ô.
- Bảng RGB/LAB của 54 stickers.
- Kết quả phân loại.
- Cube string.

Khi solver báo state invalid, dùng các log này để tìm sticker bị nhầm.

## Lưu Ý Theo Bản Vẽ Cơ Khí

- Camera nhìn từ trên cao, có thể chụp mặt trên của cube rõ nhất.
- Nếu cần quét đủ 6 mặt, robot phải đưa cube qua các `SCAN_POSE` khác nhau hoặc người dùng xoay cube theo hướng dẫn.
- Các cụm trượt chéo quanh cube có thể tạo bóng đổ, nên đèn LED nên đặt gần camera hoặc dùng tán sáng.
- Nên thêm ảnh debug overlay để kiểm tra đầu kẹp/cơ cấu giữ có che sticker nào không.
