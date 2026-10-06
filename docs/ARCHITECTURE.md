# Kien Truc He Thong

## Data Flow

```text
capture images
  -> sticker extraction
  -> color classification
  -> cube state
  -> state validation
  -> solver moves
  -> robot actions
  -> UART frames
  -> STM32 servo scheduler
```

## Co Khi Theo Ban Ve Hien Tai

Theo cac anh CAD trong `technical drawing/`, he thong nen duoc coi la robot co:

- Camera co dinh tren khung nhom, nhin tu tren xuong.
- 4 cum actuator truot cheo quanh Rubik.
- Cum giu/xoay gan cube.
- Cum trung tam duoi mat ban co kha nang nang/xoay/dinh vi.

Vi vay kien truc dieu khien nen tach thanh 2 lop:

1. `cube move planner`: xu ly cac buoc Rubik `U R F D L B`.
2. `machine action planner`: chuyen cac buoc Rubik thanh action theo actuator thuc te nhu `approach`, `clamp`, `turn`, `release`, `retract`.

Chi tiet nam trong [MECHANICAL_DESIGN.md](MECHANICAL_DESIGN.md) va [ACTUATOR_MAPPING.md](ACTUATOR_MAPPING.md).

## Raspberry Pi 4

### Vision

Trach nhiem:

- Lay anh tu camera.
- Cat vung Rubik.
- Lay mau trung binh cua 9 sticker.
- Phan loai mau theo calibration.
- Sinh cube string theo thu tu solver.

File lien quan:

- `rpi/rubik_robot/vision/capture.py`
- `rpi/rubik_robot/vision/color_classifier.py`
- `rpi/rubik_robot/cube/state.py`

### Solver

Trach nhiem:

- Nhan cube string 54 ky tu.
- Kiem tra format co ban.
- Goi solver Kociemba neu thu vien co san.
- Co fallback demo neu chua cai solver.

File lien quan:

- `rpi/rubik_robot/solver/kociemba_solver.py`

### Motion Planner

Trach nhiem:

- Chuyen cube moves thanh robot actions.
- Uoc luong cost cho tung chuoi action.
- La noi mo rong de toi uu "huong giai nhanh nhat" theo co khi thuc te.
- Voi ban ve hien tai, motion planner phai tinh them cost cho 4 cum truot cheo va cum trung tam, khong chi dem so buoc Rubik.

File lien quan:

- `rpi/rubik_robot/motion/planner.py`

### Transport

Trach nhiem:

- Dong goi lenh ASCII.
- Gui qua UART.
- Doi ACK/NACK va retry.

File lien quan:

- `rpi/rubik_robot/transport/serial_link.py`
- `rpi/rubik_robot/protocol.py`

## STM32

STM32 nen chi lam cac viec thoi gian thuc, don gian va chac chan:

- Nhan lenh UART.
- Parse lenh.
- Dieu khien PWM servo.
- Quan ly trang thai `IDLE`, `BUSY`, `ERROR`, `STOPPED`.
- Tra loi `OK`, `ERR`, `DONE`.

Khong nen dua solver hoac xu ly anh vao STM32.

## Chuoi Trang Thai De Xuat

```text
BOOT
  -> IDLE
  -> HOMING
  -> IDLE
  -> EXECUTING_MOVE
  -> IDLE
  -> ERROR or STOPPED
```

## Toi Uu Huong Giai Nhanh

Kociemba toi uu so buoc cube, nhung robot can toi uu thoi gian co khi. Nen tach thanh 2 tang:

1. Solver sinh mot hoac nhieu solution ung vien.
2. Motion planner tinh cost robot cho tung solution/hurong dat cube.

Cost co the gom:

- So lan reorient cube.
- So lan grip/release.
- Tong goc quay servo.
- Delay an toan.
- Penalty cho mat kho thao tac.

Ban dau co the chon solution dau tien. Khi co hardware that, cap nhat cost model theo thoi gian do duoc.

