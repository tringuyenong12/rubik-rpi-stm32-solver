# Rubik RPi STM32 Solver

He thong giai Rubik 3x3x3 dung Raspberry Pi 4 de xu ly anh va tim loi giai, STM32 de dieu khien servo/driver co cau kep xoay.

## Muc Tieu

- Ghi nhan 6 mat Rubik bang camera.
- Phan loai mau va chuan hoa trang thai cube theo dinh dang solver.
- Kiem tra trang thai hop le truoc khi giai.
- Tim chuoi buoc giai bang solver 2-phase/Kociemba.
- Bien chuoi buoc `R U R' U' ...` thanh lenh servo/motion.
- Gui lenh tu Raspberry Pi 4 sang STM32 qua UART.
- STM32 dieu khien servo theo chuoi lenh an toan, co ACK/NACK va trang thai loi.

## Chuc Nang Bat Buoc

1. Giai Rubik 3x3x3 tu dong.
   - He thong tu scan trang thai Rubik, tim loi giai, lap ke hoach chuyen dong va dieu khien servo de giai cube.

2. Tao de bai tron Rubik theo muc do.
   - Phan mem sinh chuoi tron Rubik theo cac cap do, vi du de, trung binh, kho.
   - Moi de bai can luu duoc scramble, trang thai cube sau khi tron va dap an giai.

3. Huong dan giai va hien thi cac buoc giai Rubik cho nguoi choi.
   - Giao dien/CLI hien thi tung buoc giai theo ky hieu Rubik.
   - Co the hien thi mo ta de hieu cho nguoi moi, vi du xoay mat nao, theo chieu nao, bao nhieu lan.
   - Chuc nang nay dung chung solver voi che do giai tu dong, nhung dau ra la huong dan cho nguoi choi thay vi lenh servo.

## Kien Truc Nhanh

```text
Camera
  -> Raspberry Pi 4
      -> Vision: capture, perspective correction, color classification
      -> Cube state validation
      -> Solver: Kociemba / 2-phase
      -> Motion planner: cube moves -> robot actions
      -> UART protocol
  -> STM32
      -> Command parser
      -> Servo scheduler
      -> Safety timeout / homing
  -> Servo + co cau kep/xoay Rubik
```

## Cau Truc Repo

```text
docs/                   Tai lieu plan, kien truc, giao tiep, pipeline CV
rpi/                    Code chay tren Raspberry Pi 4
firmware/stm32cubeide/  Firmware STM32 theo workflow STM32CubeIDE/CubeMX
mechanical/             Ghi chu co khi, calibration va test motion
technical drawing/      Anh ban ve/CAD cua thiet ke co khi hien tai
calibration/            Noi luu thong so mau/servo theo phan cung thuc
scripts/                Script tien ich cho demo/test
```

## Quick Start Cho Raspberry Pi

```bash
cd rpi
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m rubik_robot.main --mode demo
pytest
```

Tren Windows PowerShell:

```powershell
cd rpi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m rubik_robot.main --mode demo
pytest
```

Theo mapping co khi moi, CLI mac dinh xuat lenh xoay mat bang `TURN`. Neu muon test firmware cu voi lenh `MOVE`:

```bash
python -m rubik_robot.main --mode demo --face-turn-command MOVE
```

Neu muon cai package o che do editable:

```bash
cd rpi
pip install -e .
rubik-robot --mode demo
```

## Quick Start Cho STM32CubeIDE

Firmware duoc to chuc theo STM32CubeIDE/CubeMX. Tao project CubeIDE, cau hinh UART + TIM PWM, sau do copy `firmware/stm32cubeide/App` vao project.

Mac dinh firmware nhan frame UART dang ASCII:

```text
MOVE U 1 400
MOVE R -1 400
HOME
PING
```

Xem chi tiet trong [docs/CUBEIDE_SETUP.md](docs/CUBEIDE_SETUP.md) va [docs/UART_PROTOCOL.md](docs/UART_PROTOCOL.md).

## Roadmap

1. Demo pipeline bang anh mau tinh: nhan dien 54 stickers va sinh cube string.
2. Giai cube string bang solver va in chuoi buoc.
3. Mo phong motion planner, dem so thao tac servo.
4. Chay UART loopback RPi <-> STM32.
5. Dieu khien tung servo rieng, calibration goc.
6. Chay full cycle voi Rubik that.

Chi tiet nam trong [docs/PLAN.md](docs/PLAN.md).

Danh sach vat tu goi y nam trong [docs/BOM.md](docs/BOM.md).

Thiet ke co khi theo ban ve CAD duoc tong hop trong [docs/MECHANICAL_DESIGN.md](docs/MECHANICAL_DESIGN.md) va mapping actuator trong [docs/ACTUATOR_MAPPING.md](docs/ACTUATOR_MAPPING.md).

## Trang Thai Hien Tai

Repo nay la bo khung ban dau cho do an. Code Python co demo solver/motion/protocol, firmware STM32 co parser lenh co ban. Cac thong so camera, mau, servo va co khi can duoc calibration theo phan cung thuc te.

