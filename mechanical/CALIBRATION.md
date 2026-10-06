# Calibration Co Khi Va Servo

## Bang Servo

Cap nhat bang nay sau khi lap phan cung. Theo ban ve CAD hien tai, nen tach actuator thanh cum truot, dau tac dong va cum trung tam thay vi chi dat ten servo 0-5.

| Channel | Chuc Nang | Home us | Min us | Max us | Ghi Chu |
|---|---|---:|---:|---:|---|
| 0 | carriage_nw hoac tool_nw | 1500 | 1000 | 2000 | TBD |
| 1 | carriage_ne hoac tool_ne | 1500 | 1000 | 2000 | TBD |
| 2 | carriage_sw hoac tool_sw | 1500 | 1000 | 2000 | TBD |
| 3 | carriage_se hoac tool_se | 1500 | 1000 | 2000 | TBD |
| 4 | center_lift | 1500 | 1000 | 2000 | optional/TBD |
| 5 | center_rotate | 1500 | 1000 | 2000 | optional/TBD |

Xem them [docs/ACTUATOR_MAPPING.md](../docs/ACTUATOR_MAPPING.md).

## Quy Trinh Calibration

1. Thao Rubik ra khoi robot.
2. Gui `SERVO <channel> 1500 300`.
3. Tim gioi han co khi an toan bang buoc nho 20-50 us.
4. Ghi lai `min`, `home`, `max`.
5. Lap Rubik vao va thu grip/release voi toc do cham.
6. Test quay 90 do, sau do 180 do.
7. Ghi lai thoi gian toi thieu khong truot cube.

## Calibration Cho 4 Cum Truot Cheo

1. Thao Rubik ra khoi ban may.
2. Home tung cum truot, ghi lai vi tri an toan.
3. Cho cum truot tien vao cham, dung truoc khi dau tac dong cham vao cube.
4. Lap Rubik vao, test `approach` voi toc do cham.
5. Danh dau 3 vi tri:
   - `home`: lui het ve an toan.
   - `approach`: gan cube nhung chua tao luc lon.
   - `engaged`: du giu/xoay mat cube.
6. Lap lai cho `carriage_nw`, `carriage_ne`, `carriage_sw`, `carriage_se`.

Neu co limit switch, moi cum truot phai home thanh cong truoc khi cho phep chay solver.

## Luu Y Nguon

Khong cap servo truc tiep tu chan 5V cua Raspberry Pi. Servo can nguon rieng, dong du lon. GND cua nguon servo, STM32 va Raspberry Pi phai noi chung.

