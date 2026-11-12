# Nhan UART va xu ly RUBIK MOVE

USART1: 115200 baud, 8N1. Gui moi lenh tren mot dong, ket thuc bang LF hoac CRLF:

```text
#1 RUBIK MOVE U\n
#999999999999999999999999999999 RUBIK MOVE R\n
```

- `UART_Command_Init(&huart1)`: bat dau nhan byte bang ngat, goi mot lan.
- `UART_Command_RxCallback(huart)`: ghep byte thanh dong; callback HAL da goi ham nay.
- `UART_Command_Process()`: tach ID, nhom, hanh dong, tham so mat; kiem tra va goi ham quay.
- `UART_Handle_Process()`: goi `UART_Command_Process()`, dung trong `while (1)`.

ID sau `#` la chuoi chu so, khong doi sang kieu so nen khong bi gioi han
boi uint32_t hay uint64_t. ID hien chi duoc doc va kiem tra, chua tra phan hoi.
Tong dong van toi da 63 byte truoc LF theo `UART_HANDLE_LINE_SIZE`; tang
hang so nay neu can dong dai hon, khong phai thay kieu so cua ID.

Cac tham so phai dung dang `#ID RUBIK MOVE MAT`, voi MAT la `U D L R F B`.
Vi du `U` goi `Rubik_UpToFront()`, `R` goi `Rubik_Right()`.
Chua xu ly hau to `'`/`2`, nhom lenh khac hoac nhieu mat trong mot dong.
Lenh sai, thieu/thua tham so, dong qua dai bi bo qua.
Chi co mot bo dem: dong gui them khi dang cho/xu ly lenh truoc se bi bo.

Trong `main.c`, loi goi UART hien dang comment. Khi chay bang UART:

```c
// Sau khi khoi tao UART va co cau:
UART_Command_Init(&huart1);

// Trong while (1), thay cho cac loi goi quay thu tu dong:
UART_Handle_Process(); // Hoac UART_Command_Process(), chi can goi mot ham.
```

Khong tu goi them `UART_Command_RxCallback()` neu dang dung callback HAL
trong module nay, vi mot byte chi duoc xu ly mot lan.

Kiem thu: `python tests/run_tests.py --uart-only` (can GCC).
