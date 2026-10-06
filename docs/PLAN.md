# Plan Do An: He Thong Giai Rubik 3x3x3

## 1. Pham Vi

He thong gom 3 khoi chinh:

- Raspberry Pi 4: camera, xu ly anh, solver, motion planner, giao tiep UART.
- STM32: nhan lenh, dieu khien servo, phan hoi trang thai, bao ve timeout.
- Co khi: khung giu Rubik, servo kep/xoay, camera mount, den chieu sang on dinh.

Muc tieu thuc te nen la "giai on dinh" truoc, sau do moi toi uu toc do.

## 2. Yeu Cau Chuc Nang

- Chuc nang 1: Giai Rubik 3x3x3 tu dong.
  - Quet trang thai Rubik bang camera.
  - Phan loai mau va tao cube string.
  - Tim loi giai bang solver.
  - Chuyen loi giai thanh chuoi action robot.
  - Gui lenh cho STM32 dieu khien servo de giai Rubik.

- Chuc nang 2: Tao de bai tron Rubik theo muc do.
  - Sinh scramble theo muc do `de`, `trung_binh`, `kho`.
  - Dam bao scramble hop le va co the giai nguoc lai.
  - Luu thong tin de bai: ten muc do, chuoi tron, cube state sau khi tron, loi giai mau.
  - Co the dung cho che do luyen tap hoac demo.

- Chuc nang 3: Huong dan giai va hien thi cac buoc giai Rubik cho nguoi choi.
  - Hien thi chuoi buoc giai theo ky hieu Rubik, vi du `R U R' U'`.
  - Giai thich tung buoc bang ngon ngu de hieu.
  - Cho phep nguoi choi xem tung buoc, quay lai buoc truoc, hoac xem toan bo loi giai.
  - Tai su dung solver cua che do tu dong, nhung khong gui lenh servo neu nguoi dung chi muon hoc/cam tay giai.

## 3. Yeu Cau Chuc Nang Chi Tiet Cho Che Do Tu Dong

- Quet du 6 mat Rubik hoac chup 6 huong cua cube.
- Phan loai 6 mau: W, Y, R, O, B, G.
- Sinh cube string 54 ky tu theo thu tu `URFDLB`.
- Kiem tra trang thai: dung 9 sticker/mau, center hop le, solver chap nhan.
- Tim loi giai.
- Chuyen loi giai thanh lenh robot.
- STM32 thuc thi lenh va bao ACK/NACK.
- Co che dung khan cap bang nut bam hoac lenh `STOP`.

## 4. Yeu Cau Phi Chuc Nang

- Anh chup on dinh duoi cung mot nguon sang.
- Sai so servo duoc calibration rieng cho tung truc.
- Sau moi lenh quan trong co xac nhan trang thai.
- Log day du: anh dau vao, mau da phan loai, cube string, solution, action list, UART transcript.

## 5. De Xuat Phan Cung

- Raspberry Pi 4, camera module hoac USB camera.
- STM32F103/STM32F401/STM32F411 hoac board tuong duong co timer PWM.
- Servo MG996R/DS3218 cho truc can moment lon.
- Nguon servo rieng 5-6V, dong du lon; noi chung GND voi STM32/RPi.
- Den LED vong hoac LED panel de giam bong do.
- Nut E-STOP cat tin hieu enable servo hoac cat nguon servo.

## 6. Kien Truc Co Khi Theo Ban Ve

Theo cac anh CAD da them vao repo, phuong an co khi hien tai la:

- Camera gan tren khung nhom cao, nhin xuong cube.
- 4 cum truot cheo quanh cube, co co cau rack-pinion.
- Cac dau tac dong/giu mat cube nam gan trung tam.
- Cum trung tam duoi mat ban co kha nang nang/xoay/dinh vi cube.

Vi vay repo se uu tien motion planner theo actuator role thay vi phuong an 2 kep don gian. Chi tiet nam trong [MECHANICAL_DESIGN.md](MECHANICAL_DESIGN.md) va [ACTUATOR_MAPPING.md](ACTUATOR_MAPPING.md).

## 7. Cac Moc Thuc Hien

### Giai Doan 1: Nen Tang

- Tao repo, chuan code, docs.
- Chay demo solver bang cube state co san.
- Tao UART protocol va loopback test.
- Viet firmware nhan `PING`, `HOME`, `MOVE`, `STOP`.

San pham: demo terminal RPi gui lenh, STM32 tra `OK`.

### Giai Doan 2: Thi Giac May Tinh

- Co dinh camera va den.
- Chup anh tung mat.
- Xac dinh 9 o sticker bang grid hoac ArUco/reference frame.
- Chuyen RGB sang HSV/LAB.
- Calibration mau tu 6 center stickers.
- Xuat cube string va anh debug co overlay.

San pham: quet 6 mat va tao cube string hop le.

### Giai Doan 3: Solver Va Motion Planner

- Tich hop solver Kociemba.
- Map move cube `U D L R F B` sang action robot.
- Them action cost de chon huong giai/motion ngan hon.
- Mo phong action list tren terminal.

San pham: tu cube string -> solution -> robot actions.

### Giai Doan 4: Dieu Khien Servo

- Calibration tung servo: home, grip, release, rotate +90, rotate -90.
- Tao profile toc do co delay an toan.
- Test tung action: grip, release, rotate face, reorient cube.
- Them retry khi STM32 NACK hoac timeout.

San pham: robot thuc thi chuoi action ngan, khong lam roi cube.

### Giai Doan 5: Chuc Nang Luyen Tap

- Sinh scramble theo muc do.
- Tao mode hien thi huong dan giai tung buoc.
- Them mo ta than thien cho nguoi moi hoc Rubik.
- Log de bai va loi giai de dung trong bao cao/demo.

San pham: nguoi choi co the lay de tron Rubik va xem huong dan giai tung buoc.

### Giai Doan 6: Full System

- Quet cube that.
- Giai cube voi robot.
- Tao de bai, tron cube, sau do robot/human co the giai theo solution.
- Do thoi gian, ti le thanh cong, so buoc, so action.
- Tinh chinh anh sang, threshold, servo timing.

San pham: video demo va so lieu danh gia.

## 8. Ke Hoach 8 Tuan Goi Y

| Tuan | Muc Tieu | Dau Ra |
|---|---|---|
| 1 | Kien truc, repo, giao tiep co ban | README, UART protocol, demo CLI |
| 2 | Firmware PWM/servo | Dieu khien tung servo |
| 3 | Camera capture va calibration mau | Anh debug 6 mat |
| 4 | Cube state validation va solver | Solution in terminal |
| 5 | Motion planner | Action list va cost |
| 6 | Sinh scramble va huong dan tung buoc | Che do luyen tap cho nguoi choi |
| 7 | Lap rap co khi, calibration | Bang goc servo |
| 8 | Toi uu, bao cao, video | Demo va report |

## 9. Rui Ro Va Cach Giam

- Anh sang thay doi: dung den co dinh, chup mau center moi lan quet.
- Servo khong du moment: dung servo kim loai, nguon rieng, giam ma sat co khi.
- Rubik bi ket: dung cube speed cube, giam toc, can chinh kep.
- Solver nhan state sai: log anh + overlay + histogram de debug.
- Giao tiep mat goi: co ACK/NACK, sequence id, timeout, retry.

## 10. Tieu Chi Danh Gia

- Ti le nhan dien mau dung tren tap anh test.
- Ti le cube state hop le sau khi scan.
- Thoi gian trung binh tu scan den solution.
- So move solver va so action robot.
- So luong de bai tao duoc theo tung muc do.
- Do dung cua loi giai hien thi cho nguoi choi.
- Ti le giai thanh cong trong 10 lan thu.
- Thoi gian giai trung binh.

