# Bill Of Materials Gợi Ý

## Xử Lý Và Điều Khiển

| Hạng Mục | Số Lượng | Ghi Chú |
|---|---:|---|
| Raspberry Pi 4 | 1 | Xử lý ảnh, solver, giao tiếp UART |
| Camera module/USB camera | 1 | Ưu tiên camera có focus cố định |
| STM32 board | 1 | Blue Pill F103, F401/F411 hoặc tương đương |
| ST-Link | 1 | Nạp firmware STM32 |
| Thẻ microSD | 1 | Raspberry Pi OS |

## Cơ Cấu Và Servo

| Hạng Mục | Số Lượng | Ghi Chú |
|---|---:|---|
| Servo metal gear | TBD | Theo số đầu kẹp/đầu xoay thực tế |
| Motor cho rack-pinion | 4 | Mỗi cụm trượt chéo cần một cơ cấu tiến/lùi |
| Driver motor/stepper | 4 | Tùy loại motor của cụm trượt |
| Linear rail/shaft trượt | 4 | Theo bản vẽ 4 cụm chéo |
| Rack + pinion | 4 | Cơ cấu tiến/lùi vào cube |
| Khung robot | 1 | Gỗ/acrylic/nhôm định hình theo bản vẽ |
| Nhôm định hình gắn camera | 1 bộ | Camera gắn cố định trên cao |
| Speed cube 3x3 | 1-2 | Cube quay mượt sẽ giảm lỗi |
| Vòng bi/trục/khớp nối | TBD | Theo thiết kế cơ khí |
| Nút E-STOP | 1 | Nên có để cắt enable/nguồn servo |

## Nguồn Và Điện

| Hạng Mục | Số Lượng | Ghi Chú |
|---|---:|---|
| Nguồn 5V cho RPi | 1 | Theo khuyến nghị của board |
| Nguồn servo 5-6V | 1 | Dòng đủ lớn, tách với RPi |
| Buck converter | 1 | Nếu dùng pin/adapter áp cao |
| Dây jumper/terminal block | TBD | Nối UART, PWM, GND |
| LED panel/ring light | 1 | Giữ ánh sáng ổn định |

## Lưu Ý

- GND Raspberry Pi, STM32 và nguồn servo phải nối chung.
- Không cấp servo từ Raspberry Pi.
- Nên tách dây nguồn servo và dây tín hiệu camera để giảm nhiễu.
- Bốn cụm trượt nếu dùng motor dòng lớn nên có nguồn/driver riêng, STM32 chỉ phát tín hiệu điều khiển.
