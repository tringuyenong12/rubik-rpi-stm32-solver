# Thiet Ke Co Khi Theo Ban Ve

Tai lieu nay tong hop tu cac anh CAD trong thu muc `technical drawing/`. Mot so diem ben duoi la suy luan tu hinh anh, can xac nhan lai bang kich thuoc va danh sach linh kien thuc te.

## Tong Quan

Thiet ke hien tai phu hop voi cau truc robot giai Rubik dang ban may co dinh:

- Camera dat tren khung nhom dinh hinh, nhin xuong Rubik tu phia tren.
- Rubik nam o trung tam ban may.
- Bon cum tac dong bo tri cheo quanh Rubik theo dang chu X.
- Moi cum co ray truot/linear rail va co cau rack-pinion de tien/lui vao Rubik.
- Gan trung tam co cac cum kep/giu mat cube.
- Duoi mat ban co mot cum co khi trung tam, co kha nang la co cau nang, xoay hoac dinh vi cube.
- Khung duoi va mat ban tao thanh mot module co the dat STM32, driver, nguon servo/motor.

## Cac Cum Chinh

### 1. Cum Camera Tren Cao

Quan sat tu anh:

- Khung nhom dinh hinh dung + ngang tao can gan camera.
- Camera huong xuong vung Rubik.
- Vi tri camera co dinh, phu hop voi pipeline grid co dinh.

Y nghia cho phan mem:

- Pipeline thi giac co the uu tien `fixed_grid_scan`.
- Nen calibration mot lan cac diem 9 sticker tren anh, sau do luu vao `calibration/color_profile.json`.
- Can them buoc kiem tra cube co nam dung tam truoc khi phan loai mau.

### 2. Bon Cum Truot Cheo

Quan sat tu anh top view:

- Co 4 cum ray truot dat cheo vao tam cube.
- Moi cum co ban truot va co cau banh rang/thanh rang.
- Cac cum nay co the dung de dua dau kep/dau xoay vao mat Rubik.

Dat ten trong repo:

```text
carriage_nw
carriage_ne
carriage_sw
carriage_se
```

Trong do `nw/ne/sw/se` la cach dat ten theo goc nhin tu camera top-down, chua phai toa do vat ly bat buoc.

Y nghia cho firmware:

- Neu dung servo lien tuc/DC motor/stepper cho rack-pinion, can driver rieng va cam bien hanh trinh.
- Neu dung servo goc cho co cau gan tren carriage, can them kenh PWM.
- STM32 nen quan ly tung cum nhu mot actuator co trang thai: `HOME`, `APPROACH`, `ENGAGED`, `RETRACTED`, `ERROR`.

### 3. Cum Giu/Xoay Gan Cube

Quan sat tu anh:

- Co cac chi tiet mau nau dat quanh cube, giong cum kep/giu mat.
- Cac cum nay co the giu cube trong luc mat khac xoay, hoac dinh vi cube khi scan.

Y nghia cho motion planner:

- Khong nen map truc tiep moi move `R/U/F/...` thanh mot servo duy nhat.
- Nen co lop trung gian: `cube move -> robot action sequence`.
- Robot action co the gom: `approach`, `clamp`, `turn_face`, `release`, `retract`, `reorient`.

### 4. Cum Trung Tam Duoi Mat Ban

Quan sat tu anh:

- Duoi mat ban co mot module mau xanh/do/xanh duong, lien ket voi truc/gear o trung tam.
- Co kha nang la co cau nang, xoay cube, hoac ho tro scan/can chinh vi tri.

Y nghia cho firmware:

- Can tach actuator trung tam thanh cac role rieng, vi du:
  - `center_lift`
  - `center_rotate`
  - `center_lock`
- Neu dung co cau nay de doi huong cube, motion planner phai tinh cost cho thao tac reorient.

## Kien Truc Dieu Khien Phu Hop

Thay vi coi STM32 chi dieu khien 4 servo, repo nen theo cau truc:

```text
RPi solver
  -> cube moves
  -> machine action planner
  -> high-level UART commands
STM32
  -> actuator state machine
  -> servo PWM / motor driver / limit switch
  -> ACK / DONE / ERR
```

## Cac Thong Tin Can Xac Nhan

De chot mapping chinh xac, can bo sung:

- Moi cum truot dung motor gi: servo goc, servo lien tuc, DC gear motor hay stepper.
- Co cam bien hanh trinh/home switch khong.
- Co bao nhieu kenh servo tong cong.
- Cum trung tam duoi mat ban co chuc nang chinh xac la nang, xoay, hay ca hai.
- Cac dau kep co the xoay mat Rubik 90/180 do truc tiep hay chi giu cube.
- Cube duoc scan bang camera mot lan tu tren, hay robot se xoay cube de chup du 6 mat.

## Quyet Dinh Thiet Ke Trong Repo

Theo ban ve, repo se uu tien phuong an:

- Camera co dinh tren cao.
- Bon cum actuator cheo quanh cube.
- STM32 dieu khien actuator theo state machine.
- RPi van giu vai tro vision, solver, tao de bai, huong dan giai va motion planning.
- Giao thuc UART mo rong dan tu lenh debug `SERVO` sang cac lenh high-level nhu `ACTUATOR`, `CLAMP`, `TURN`, `SCAN_POSE`.

