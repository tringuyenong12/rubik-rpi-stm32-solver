# Danh Mục Bản Vẽ Kỹ Thuật

Thư mục ảnh:

```text
technical drawing/
```

## Ảnh Đã Kiểm Tra

| File | Nội Dung Chính |
|---|---|
| `1790372684930_509213780918941956_g4262955945264954684_b0a718d6b400063eade5af45e214af50.jpg` | Mặt đứng: camera trên cao, cube ở trung tâm, cụm dưới bàn, hai cụm bên trái/phải |
| `1790372759020_509213780918941956_g4262955945264954684_99084e95579a433a889d9904ed7fd9aa.jpg` | Phối cảnh dưới bàn: thấy module trung tâm và khung mặt bàn |
| `1790372868189_509213780918941956_g4262955945264954684_608765de8fd3643e5fd9632b34832dbf.jpg` | Top view: 4 cụm trượt chéo quanh cube, rack-pinion, camera gắn trên thanh ngang |
| `1790379674572_509213780918941956_g4262955945264954684_eac12e7af25054847ddd3438737438a6.jpg` | Phối cảnh trước: cube được giữ ở trung tâm, camera cố định |
| `1790379692257_509213780918941956_g4262955945264954684_84aff6bef5627de126e28e06ecb19cac.jpg` | Phối cảnh chéo: thấy rõ các cụm tác động xung quanh cube |
| `1790382306351_509213780918941956_g4262955945264954684_8ec8ca7c2b1bd3b95467ccb4321d5693.jpg` | Phối cảnh sau/dưới: thấy module dưới bàn và vị trí linh kiện điện |

## Kết Luận Cho Repo

Repo sẽ không còn coi cơ khí là phương án 2 kẹp đơn giản. Thiết kế phù hợp hơn là:

- 4 cụm trượt chéo.
- 1 cụm camera cố định trên cao.
- 1 cụm trung tâm dưới mặt bàn.
- Điều khiển theo actuator role, không hard-code từng servo ngay từ đầu.
