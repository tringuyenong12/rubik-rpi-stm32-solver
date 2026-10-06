# Pipeline Thi Giac May Tinh

## Thu Tu Scan

Dung quy uoc solver `URFDLB`:

- U: Up
- R: Right
- F: Front
- D: Down
- L: Left
- B: Back

Khi chup 6 mat, can co jig/cach dat cube co lap lai de khong nham huong. Neu dung robot de xoay cube trong luc scan, moi thao tac scan nen duoc log lai.

## Pipeline De Xuat

1. Capture anh.
2. Can bang trang hoac khoa exposure cua camera.
3. Tim vung Rubik:
   - Theo ban ve hien tai, camera duoc gan co dinh tren cao nen uu tien dung grid co dinh.
   - Them buoc kiem tra tam cube vi cac cum actuator co the che mot phan vien cube.
   - Nang cao: detect contour/ArUco/reference frame tren jig trung tam.
4. Lay mau vung trung tam cua 9 sticker.
5. Chuyen mau sang LAB hoac HSV.
6. Dung 6 center stickers lam mau tham chieu moi lan scan.
7. Gan moi sticker vao mau center gan nhat.
8. Kiem tra moi mau co dung 9 stickers.
9. Xuat cube string va anh debug overlay.

## Calibration

Nen luu file `calibration/color_profile.json` gom:

- Dieu kien anh sang.
- Camera id/resolution.
- Vi tri 9 o tren anh.
- Mau center trung binh.
- Threshold khoang cach mau.

## Debug Bat Buoc

Moi lan scan nen luu:

- Anh goc.
- Anh overlay danh dau 9 o.
- Bang RGB/LAB cua 54 stickers.
- Ket qua phan loai.
- Cube string.

Khi solver bao state invalid, dung cac log nay de tim sticker bi nham.

## Luu Y Theo Ban Ve Co Khi

- Camera nhin tu tren cao, co the chup mat tren cua cube ro nhat.
- Neu can quet du 6 mat, robot phai dua cube qua cac `SCAN_POSE` khac nhau hoac nguoi dung xoay cube theo huong dan.
- Cac cum truot cheo quanh cube co the tao bong do, nen den LED nen dat gan camera hoac dung tan sang.
- Nen them anh debug overlay de kiem tra dau kep/co cau giu co che sticker nao khong.

