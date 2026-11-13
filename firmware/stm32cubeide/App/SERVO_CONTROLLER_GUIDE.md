# Thư viện servo cho STM32

Dùng đồng thời `servo_controller.h` và `servo_controller.c`: file .h khai báo API, file .c thực hiện điều khiển. Copy hai file vào App của project CubeIDE và thêm App vào include path.

Thư viện dành cho **servo điều khiển vị trí**, bao gồm servo 270°, không phải servo quay liên tục. Chưa có bảng PWM đo thực tế trong repository nên không có khớp nào tự bật sau Init.

## Thay đổi so với bản cũ

- Mỗi kênh có timer handle riêng. Kênh TIM3 không còn ghi nhầm vào TIM2.
- Tối đa 10 kênh logic; mỗi role dùng một đầu ra PWM riêng.
- Phải ConfigProfile trước Start. Không có profile thì Start trả false và không bật PWM.
- Start, ConfigProfile và Home trả bool; ứng dụng phải kiểm tra kết quả.
- ConfigChannel phải gọi trước ConfigProfile của kênh đó. Cấu hình bị khóa sau khi Start thành công.
- TurnFace/MoveFace/ScanPose trả false do chưa có sequence cơ khí; snippet UART trả ERR UNSUPPORTED.
- Stop giữ PWM cuối và khóa lệnh mới; servo vẫn có thể đi tới đích cuối. Đây không phải dừng khẩn cấp.

## Thứ tự cấu hình

1. CubeMX khởi tạo timer/chân PWM, chưa gọi HAL_TIM_PWM_Start ở nơi khác.
2. Init.
3. ConfigChannel: ánh xạ timer/kênh vật lý.
4. ConfigProfile: nạp giới hạn và các mốc PWM đã đo.
5. ConfigAngles nếu cần điều khiển theo góc.
6. Start và kiểm tra kết quả.

Init với &htim2 tạo sẵn chỉ số 0–3 tương ứng TIM2 CH1–4, bộ đếm 1 MHz. Init với NULL cho phép khai báo toàn bộ ánh xạ riêng. Role chưa ConfigProfile không nhận lệnh và không bật PWM.

Không sửa trực tiếp các trường trong ServoController. Chỉ gọi API từ một vòng lặp/task, không gọi đồng thời từ ngắt. Không Init lại khi PWM đang chạy.

## Timer và đơn vị

Cấu hình PWM mode 1, active high, đếm lên, edge-aligned. Tần số PWM cần phù hợp thông số servo. Ví dụ 50 Hz trong dự án: clock timer 72 MHz, PSC = 71, ARR = 19999.

counter_hz là tần số bộ đếm **sau prescaler**, không phải SYSCLK:

| Bộ đếm | ARR cho 50 Hz | CCR ứng với 1500 µs |
|---|---:|---:|
| 1 MHz | 19999 | 1500 |
| 2 MHz | 39999 | 3000 |

Thư viện đổi µs sang tick và làm tròn; không tự sửa PSC/ARR/chân PWM. CCR phải lớn hơn 0 và nhỏ hơn chu kỳ. Nếu bảng đo ghi giá trị CCR, cần tần số bộ đếm để đổi sang µs.

## Ví dụ một khớp

**Số dưới đây chỉ minh họa API, không phải số đo của robot. Thay bằng số đo và giới hạn thực tế trước khi chạy.** Target không dùng có thể đặt bằng home.

```c
ServoController_Init(&servo_controller, NULL);
if (!ServoController_ConfigChannel(&servo_controller, 0,
                                    &htim2, TIM_CHANNEL_1, 1000000u)) {
    Error_Handler();
}

ServoProfile rotation = {
    .pwm_channel_index = 0,
    .pulse_home_us = 1510,
    .pulse_approach_us = 1510,
    .pulse_engaged_us = 1510,
    .pulse_retract_us = 1510,
    .pulse_scan_us = 1510,
    .pulse_min_us = 800,
    .pulse_max_us = 2200,
};
/* Chon role dung voi co khi; day chi la vi du. */
if (!ServoController_ConfigProfile(&servo_controller,
                                   SERVO_ROLE_CENTER_ROTATE, &rotation)) {
    Error_Handler();
}
ServoAngleCalibration angles = {
    .angle_decideg = {-900, 0, 900},
    .pulse_us = {800, 1510, 2200},
};
if (!ServoController_ConfigAngles(&servo_controller,
                                  SERVO_ROLE_CENTER_ROTATE, &angles)) {
    Error_Handler();
}
/* Them cac kenh/profile khac TRUOC Start. */
if (!ServoController_Start(&servo_controller)) {
    Error_Handler();
}
```

Thêm servo trên TIM3 bằng ConfigChannel với chỉ số khác, &htim3, kênh và tần số bộ đếm thực tế; sau đó ConfigProfile cho role khác. Timer đó phải được CubeMX khởi tạo.

Kẹp và xoay dùng hai servo thì phải có hai role/kênh riêng phù hợp cơ khí. Tên role giữ theo bản vẽ cũ; không tự suy ra chức năng chỉ từ tên góc nhìn.

## Cân chỉnh 0° và servo 270°

WriteAngle nhận tọa độ cơ cấu theo **0,1°**: -900 là -90°, 0 là 0°, 900 là +90°.

```c
bool ok = ServoController_WriteAngle(&servo_controller,
                                     SERVO_ROLE_CENTER_ROTATE, -900);
/* Kiem tra ok; cho thoi gian di chuyen phu hop co khi. */
```

Ba góc phải tăng dần; PWM phải tăng dần hoặc giảm dần (servo lắp ngược chiều). Nội suy riêng từng đoạn giữ đúng ba điểm đo, không giả định hai phía đối xứng.

Nếu bảng cũ là 0°–90°–180° và **90° là thẳng đứng**, có thể gán ba PWM đó cho -90°–0°–+90°. Nếu thẳng đứng ở vị trí khác thì cần đo lại. Muốn Home trùng WriteAngle(0), đặt pulse_home_us bằng PWM đo tại 0°.

Lắp tay servo để tư thế thẳng đứng còn đủ hành trình hai phía. Đổi tên góc trong code không tạo thêm hành trình cơ khí.

Không ngoại suy ngoài ba mốc. Đã đo -90°..+90° thì +180° bị từ chối dù servo được bán là 270°. Tổng khoảng góc hiệu chỉnh tối đa 270°.

Để xoay mặt Rubik nhiều lần cần sequence nhả kẹp, đưa khớp về và kẹp lại phù hợp cơ khí. Thư viện chưa tự thực hiện sequence này. Thay ConfigProfile sẽ xóa calibration góc cũ, cần gọi ConfigAngles lại.

## Các API còn lại

- WriteUs ghi µs vào kênh có profile và đã bật; ngoài giới hạn trả false, không tự cắt về biên.
- WriteRole dùng các mốc home/approach/engaged/retract/scan.
- SOLVE là alias của engaged, SAFE là alias của home, không có quy trình tránh va chạm.
- Clamp chỉ nhận TOOL_NW/NE/SW/SE: close dùng engaged, open dùng retract. Chỉ dùng nếu role thực sự nối servo kẹp.
- WriteAngle là API C; chưa có lệnh UART ANGLE.
- Chưa có lệnh UART nạp calibration hoặc lưu Flash; điền profile trong code ứng dụng trước Start rồi build/flash.

## Home, trạng thái và lỗi

Start/Home phát lệnh home cho các role đã cấu hình **cùng lúc**, không tự mở kẹp/rút tay, không chờ hoàn tất và không dò gốc bằng cảm biến. Ứng dụng phải đảm bảo đường đi cơ khí phù hợp.

GetState phản ánh lệnh phần mềm cuối. HOME/ENGAGED không chứng minh servo đã tới nơi vì chưa có feedback. WriteUs/WriteAngle đặt MOVING.

Stop khóa lệnh mới, giữ PWM cuối. Home kiểm tra cấu hình rồi bỏ khóa và phát home. Gọi Start lần nữa khi đang chạy bị từ chối.

Nếu HAL start lỗi, driver thử tắt các đầu ra đã bật/đã thử bật và báo ERROR. Nếu bước tắt cũng lỗi, cấu hình và Start vẫn bị khóa; ứng dụng phải xử lý lỗi HAL và khôi phục peripheral trước khi Init lại.

Snippet dùng HAL_Delay nên STOP qua UART chỉ được xử lý khi vòng lặp đọc được lệnh; không thể ngắt tức thì giữa lần chờ. Các thời gian chờ trong snippet chỉ là ước lượng.

## Thông tin cần lấy từ người cân chỉnh

| Servo/role | Timer và CH | Tần số bộ đếm | PWM ba góc đo (µs) | Mốc thẳng đứng | Min/max an toàn | PWM mở/đóng nếu là kẹp |
|---|---|---|---|---|---|---|
| Điền từng servo | | | | | | |

Khi chưa điền profile, snippet trả ERR CONFIG servo_not_ready; vẫn nhận PING qua UART nhưng không cho điều khiển servo.

## Kiểm thử trên máy tính

Từ thư mục gốc: `python firmware/tests/run_tests.py`.

Cần GCC trong PATH hoặc biến CC trỏ tới compiler. Kiểm thử dùng HAL giả lập, kiểm tra nhiều timer, giới hạn, góc hai chiều, lỗi startup, Stop/Home và biên dịch snippet main.c.

Chưa kiểm thử trên STM32 thật. Cần build với HAL của board và kiểm tra PWM/cơ cấu sau khi có bảng calibration.
