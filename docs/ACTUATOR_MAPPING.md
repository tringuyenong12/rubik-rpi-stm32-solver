# Actuator Mapping

Tai lieu nay dinh nghia cach dat ten actuator theo ban ve CAD. Day la mapping logic cho phan mem; channel STM32 thuc te se duoc dien sau khi chot motor/driver.

## Ten Actuator

| Role | Vi Tri Suy Luan | Chuc Nang |
|---|---|---|
| `carriage_nw` | Cum truot goc tren-trai theo camera top-down | Tien/lui dau tac dong vao cube |
| `carriage_ne` | Cum truot goc tren-phai theo camera top-down | Tien/lui dau tac dong vao cube |
| `carriage_sw` | Cum truot goc duoi-trai theo camera top-down | Tien/lui dau tac dong vao cube |
| `carriage_se` | Cum truot goc duoi-phai theo camera top-down | Tien/lui dau tac dong vao cube |
| `tool_nw` | Dau tac dong tren carriage_nw | Kep, giu, hoac xoay mat Rubik |
| `tool_ne` | Dau tac dong tren carriage_ne | Kep, giu, hoac xoay mat Rubik |
| `tool_sw` | Dau tac dong tren carriage_sw | Kep, giu, hoac xoay mat Rubik |
| `tool_se` | Dau tac dong tren carriage_se | Kep, giu, hoac xoay mat Rubik |
| `center_lift` | Cum duoi mat ban | Nang/ha hoac dua cube vao vi tri scan |
| `center_rotate` | Cum duoi mat ban | Xoay/dinh huong cube neu co |

## Trang Thai De Xuat

Moi actuator nen co trang thai logic:

```text
UNKNOWN
HOMING
HOME
MOVING
ENGAGED
RETRACTED
ERROR
STOPPED
```

## Lenh UART Mo Rong De Xuat

Lenh debug hien co:

```text
SERVO <channel> <pulse_us> <duration_ms>
MOVE <face> <turns> <duration_ms>
```

Lenh phu hop hon voi ban ve:

```text
ACTUATOR <role> <target> <duration_ms>
CLAMP <role> <open|close>
TURN <face> <turns> <duration_ms>
SCAN_POSE <face>
HOME
STOP
```

Vi du:

```text
ACTUATOR carriage_nw approach 500
CLAMP tool_nw close
TURN R 1 450
CLAMP tool_nw open
ACTUATOR carriage_nw retract 500
```

## Mapping Cube Face Sang Co Khi

Chua nen hard-code cho den khi test that. Ban dau dung bang sau:

| Cube Face | Tool/Carriage Du Kien | Ghi Chu |
|---|---|---|
| U | TBD | Co the can center_rotate/reorient |
| R | TBD | Can test dau tac dong gan mat phai |
| F | TBD | Can test goc nhin camera va huong cube |
| D | TBD | Co the lien quan center_lift/rotate |
| L | TBD | Can test dau tac dong gan mat trai |
| B | TBD | Co the can reorient cube |

Sau khi co hardware that, dien bang nay truoc khi toi uu motion planner.

