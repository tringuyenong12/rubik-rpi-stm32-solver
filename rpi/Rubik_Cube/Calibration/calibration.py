"""Tkinter servo calibration console. Run from any directory with Python 3.10+.

Source values are a reference, never presented as live STM32 telemetry.
Only explicit button presses send commands. SET/ADD/SUB move the selected servo
immediately; successful changes are followed by read-only refresh requests.
"""
from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import queue
import re
import threading
import tempfile
import time
from dataclasses import dataclass
from decimal import Decimal


POSITIONS = {
    "ROTATE": {"HOME": "home_angle", "CLOCK": "clockwise_angle",
               "ANTI": "anticlockwise_angle"},
    "MOVE": {"FULL_RELEASE": "full_release_angle",
             "HALF_RELEASE": "half_release_angle", "CLAMP": "clamp_angle",
             "TIGHT_CLAMP": "tight_clamp_angle"},
}
DEFAULT_SOURCE = (Path(__file__).resolve().parents[2] / "Rubik_Cube" / "Calibration" / "Servo_Control.c")
EXPORT_PATH = Path(__file__).resolve().with_name("calibration_servo_stm32.txt")


@dataclass
class ServoDefinition:
    id: int
    name: str
    kind: str
    channel: int
    fields: dict[str, float]


def load_servos(source: Path) -> list[ServoDefinition]:
    """Read each designated initializer; do not substitute generic defaults."""
    text = source.read_text(encoding="utf-8")
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    blocks = re.findall(
        r"\[(SERVO_(ROTATE|MOVE)_(FRONT|RIGHT|BACK|LEFT))\]\s*=\s*\{(.*?)\n\s*\}\s*[,}]",
        text, re.S,
    )
    sides = ("FRONT", "RIGHT", "BACK", "LEFT")
    result = {}
    for name, kind, side, block in blocks:
        servo_id = sides.index(side) + (4 if kind == "MOVE" else 0)
        channel = re.search(r"\.channel\s*=\s*(\d+)", block)
        fields = {key: float(value) for key, value in re.findall(
            r"\.(\w+_angle)\s*=\s*(-?\d+(?:\.\d+)?)[fF]?", block)}
        expected = {"current_angle", "target_angle"}
        for field in POSITIONS[kind].values():
            expected.update((field, "offset_calib_" + field))
        if channel is None or not expected.issubset(fields):
            raise ValueError(f"Thiếu channel hoặc trường góc trong {name}")
        result[servo_id] = ServoDefinition(servo_id, name, kind, int(channel[1]), fields)
    if set(result) != set(range(8)):
        raise ValueError("Không đọc được đủ 8 servo từ Servo_Control.c")
    return [result[index] for index in range(8)]


def number(text: str) -> float:
    try:
        value = float(text)
    except ValueError as exc:
        raise ValueError("Giá trị phải là số") from exc
    if not math.isfinite(value):
        raise ValueError("Không chấp nhận NaN hoặc infinity")
    return value


def servo_command(action: str, servo: ServoDefinition, position: str,
                  value: str = "") -> str:
    if action not in {"SET", "ADD", "SUB", "GET"}:
        raise ValueError("Sai hành động calibration")
    if position not in POSITIONS[servo.kind]:
        raise ValueError("Vị trí không thuộc loại servo này")
    body = f"CALIB SERVO {action} {servo.id} {position}"
    if action != "GET":
        amount = number(value)
        if not 0 <= amount <= 180:
            raise ValueError("Giá trị phải trong 0..180 độ; SUB nhận lượng giảm không âm")
        # Firmware rejects exponent notation. Do not round values with :g,
        # which can also turn a small positive number into an invalid token.
        token = format(Decimal(str(amount)), "f")
        if "." in token:
            token = token.rstrip("0").rstrip(".")
        body += " " + token
    return body


def frame(command_id: int, body: str) -> bytes:
    if not 0 <= command_id <= 65535:
        raise ValueError("Đã dùng hết ID; mở phiên kết nối mới")
    if not re.fullmatch(r"[A-Za-z0-9_.+\-]+(?: [A-Za-z0-9_.+\-]+)*", body):
        raise ValueError("Lệnh phải chứa các token ASCII, không có xuống dòng")
    wire = f"#{command_id} {body}\n".encode("ascii")
    if len(wire) - 2 >= 64:
        raise ValueError("Lệnh vượt UART_BUFFER_SIZE = 64")
    return wire


class FirmwareError(RuntimeError):
    """An explicit ERR ends this request, without desynchronizing the link."""


def export_servo_configuration(link, servos, path: Path, on_value=None):
    """Read a fresh complete snapshot; replace the file only after validation.

    This only sends GET commands. Offsets are folded into base angles in the
    generated initializer, not reset in the running STM32.
    """
    if sorted(servo.id for servo in servos) != list(range(8)):
        raise ValueError("Cần đủ 8 servo để xuất cấu hình")
    commands = []
    for servo in servos:
        commands.append((f"CALIB SERVO GET {servo.id} channel", (servo.id, "channel")))
        for position in POSITIONS[servo.kind]:
            commands.append((f"CALIB SERVO GET {servo.id} {position} REAL_ANGLE",
                             (servo.id, position + ":REAL_ANGLE")))
    for offset, (body, _) in enumerate(commands):
        frame(link.next_id + offset, body)
    snapshot = {}
    for body, destination in commands:
        value = link.request(body)
        if value is None:
            raise ValueError(f"Thiếu VALUE: {body}")
        amount = number(value)
        if destination[1] == "channel":
            if not amount.is_integer() or not 0 <= amount <= 15:
                raise ValueError(f"Channel không hợp lệ: {value}")
        elif not 0 <= amount <= 180:
            raise ValueError(f"REAL_ANGLE ngoài 0..180 độ: {body} = {value}")
        snapshot[destination] = amount
        if on_value:
            on_value(destination, value)

    lines = ["Servo_t servo[SERVO_COUNT ] =", "{"]
    for servo in sorted(servos, key=lambda item: item.id):
        lines.extend([
            f"    [{servo.name}] = {{",
            f"        .channel = {int(snapshot[servo.id, 'channel'])},",
            f"        .state.{servo.kind.lower()} = {{",
            "            .current_angle = -1.0f, .target_angle = -1.0f,",
        ])
        positions = list(POSITIONS[servo.kind].items())
        for index, (position, field) in enumerate(positions):
            angle = snapshot[servo.id, position + ":REAL_ANGLE"]
            comma = "," if index < len(positions) - 1 else ""
            lines.append(f"            .{field} = {angle:.3f}f, "
                         f".offset_calib_{field} = 0.0f{comma}")
        lines.extend(["        }", "    }" + ("," if servo.id < 7 else "")])
    lines.append("};")
    # Keep an existing export intact on UART, validation or write failure.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.write("\n".join(lines) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


class CalibrationLink:
    """One outstanding request; every command waits for DONE, GET also VALUE."""

    def __init__(self, serial_port, timeout: float = 3.0, trace=None):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("Timeout phải lớn hơn 0")
        self.serial = serial_port
        self.timeout = timeout
        self.trace = trace or (lambda *args: None)
        self.next_id = 1
        self.failed = False
        self.cancel = threading.Event()

    def request(self, body: str) -> str | None:
        if self.failed:
            raise RuntimeError("Phiên UART có lỗi; ngắt kết nối và kiểm tra STM32")
        request_id = self.next_id
        wire = frame(request_id, body)
        self.next_id += 1
        is_get = "GET" in body.split()
        result = None
        try:
            if self.cancel.is_set():
                raise InterruptedError("Đã hủy chờ UART")
            self.trace("TX", wire.decode().strip())
            if self.serial.write(wire) != len(wire):
                raise OSError("UART chỉ gửi được một phần lệnh")
            deadline = time.monotonic() + self.timeout
            pending = bytearray()
            while time.monotonic() < deadline:
                if self.cancel.is_set():
                    raise InterruptedError("Đã hủy chờ UART")
                chunk = self.serial.read(1)
                if not chunk:
                    continue
                if chunk != b"\n":
                    pending.extend(chunk)
                    if len(pending) > 256:
                        raise OSError("Phản hồi UART quá dài")
                    continue
                line = pending.decode("ascii", errors="replace").strip()
                pending.clear()
                self.trace("RX", line)
                match = re.fullmatch(r">?#(\d{1,5}) ([A-Z_]+)(?: (.*))?", line)
                if match is None or int(match[1]) != request_id:
                    continue
                status, detail = match[2], match[3] or ""
                if status == "OK" and not detail:
                    continue
                if status == "ERR":
                    raise FirmwareError(f"STM32: {detail or 'ERR'} (#{request_id})")
                if is_get and status == "VALUE" and detail:
                    number(detail)  # Never put malformed/non-finite telemetry in the UI.
                    if result is not None:
                        raise RuntimeError(f"STM32 trả VALUE nhiều lần cho #{request_id}")
                    result = detail
                    continue
                if status == "DONE" and not detail:
                    if is_get and result is None:
                        raise RuntimeError(f"STM32 trả DONE nhưng thiếu VALUE cho #{request_id}")
                    return result
                raise RuntimeError(f"STM32: {line}")
            raise TimeoutError(
                f"Chưa nhận đủ {'VALUE và DONE' if is_get else 'DONE'} cho #{request_id} "
                f"sau {self.timeout:g}s. Kiểm tra UART và firmware đã nạp; "
                "kết quả lệnh chưa xác định. Không tự gửi lại.")
        except FirmwareError:
            # Stop this batch, but allow the operator to correct a rejected value.
            raise
        except BaseException:
            # No terminal response: require a new connection after checking STM32.
            self.failed = True
            raise


class CalibrationApp:
    def __init__(self, root, servos, source, port, baudrate):
        import tkinter as tk
        from tkinter import ttk
        from tkinter.scrolledtext import ScrolledText

        self.tk, self.ttk, self.root = tk, ttk, root
        self.servos, self.source = servos, source
        self.events = queue.Queue()
        self.link = None
        self.busy = False
        self.closed = False
        self.live = {}  # Only VALUE responses populate this map.
        self.trees = {}
        self.actions = []
        root.title("Calibration — Rubik STM32 / Raspberry Pi")
        root.geometry("1100x820")
        root.minsize(850, 650)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        connection = ttk.LabelFrame(root, text="Kết nối UART • 8N1", padding=8)
        connection.grid(row=0, column=0, sticky="ew", padx=8, pady=5)
        self.port = tk.StringVar(value=port)
        self.baud = tk.StringVar(value=str(baudrate))
        self.timeout = tk.StringVar(value="3")
        for column, (label, variable, width) in enumerate(
                (("Cổng", self.port, 22), ("Baud", self.baud, 10),
                 ("Timeout (s)", self.timeout, 5))):
            ttk.Label(connection, text=label).grid(row=0, column=column * 2, padx=3)
            ttk.Entry(connection, textvariable=variable, width=width).grid(
                row=0, column=column * 2 + 1, padx=3)
        self.connect_button = ttk.Button(connection, text="Kết nối", command=self.connect)
        self.connect_button.grid(row=0, column=6, padx=6)
        self.disconnect_button = ttk.Button(connection, text="Ngắt kết nối", command=self.disconnect)
        self.disconnect_button.grid(row=0, column=7)

        ttk.Label(root, text=(
            "Đơn vị: độ (0–180). SET đặt góc sau offset; ADD/SUB tăng/giảm offset.\n"
            "SET/ADD/SUB làm servo di chuyển ngay và cập nhật RAM; không lưu qua khởi động lại.\n"
            "current_angle là góc lệnh gần nhất, không phải cảm biến. −1 = chưa gửi góc."
        ), foreground="#9a4500", wraplength=1030).grid(
            row=1, column=0, sticky="w", padx=12, pady=4)

        toolbar = ttk.Frame(root)
        toolbar.grid(row=2, column=0, sticky="ew", padx=8)
        self.button(toolbar, "Đọc servo đang chọn", self.refresh).pack(side="left", padx=3)
        self.button(toolbar, "Đọc cả 8 servo", lambda: self.refresh(all_servos=True)).pack(side="left", padx=3)
        self.button(toolbar, "Lưu cấu hình STM32 (.txt)", self.export_configuration).pack(side="left", padx=3)

        self.tabs = ttk.Notebook(root)
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=8, pady=5)
        self.position_vars = {}
        self.value_vars = {}
        for servo in servos:
            tab = ttk.Frame(self.tabs, padding=8)
            self.tabs.add(tab, text=f"{servo.id} {servo.name.split('_')[-1]} {servo.kind}")
            tab.columnconfigure(0, weight=1)
            tab.rowconfigure(1, weight=1)
            ttk.Label(tab, text=f"{servo.name}  •  ID {servo.id}  •  PCA9685 channel {servo.channel}").grid(
                row=0, column=0, sticky="w")
            tree = ttk.Treeview(tab, columns=("field", "source", "uart"), show="headings", height=10)
            for key, title, width in (("field", "Thông số", 330),
                                      ("source", "Mã nguồn (tham khảo)", 210),
                                      ("uart", "STM32 (góc/offset: độ)", 250)):
                tree.heading(key, text=title)
                tree.column(key, width=width, minwidth=100)
            scrollbar = ttk.Scrollbar(tab, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            tree.grid(row=1, column=0, sticky="nsew", pady=5)
            scrollbar.grid(row=1, column=1, sticky="ns")
            tree.insert("", "end", iid="channel", values=("channel (PCA9685)", servo.channel, "Chưa đọc"))
            for field, value in servo.fields.items():
                tree.insert("", "end", iid=field, values=(field, f"{value:g}", "Chưa đọc"))
            for position, field in POSITIONS[servo.kind].items():
                initial_angle = servo.fields[field] + servo.fields["offset_calib_" + field]
                tree.insert("", "end", iid=position,
                            values=(f"{position} (góc + offset)", f"{initial_angle:g}", "Chưa đọc"))
                tree.insert("", "end", iid=position + ":REAL_ANGLE",
                            values=(f"{position} REAL_ANGLE", f"{initial_angle:g}", "Chưa đọc"))
            self.trees[servo.id] = tree
            controls = ttk.Frame(tab)
            controls.grid(row=2, column=0, sticky="ew", pady=5)
            position = tk.StringVar(value=next(iter(POSITIONS[servo.kind])))
            value = tk.StringVar(value="0.5")
            self.position_vars[servo.id], self.value_vars[servo.id] = position, value
            ttk.Combobox(controls, textvariable=position, values=tuple(POSITIONS[servo.kind]),
                         state="readonly", width=18).pack(side="left", padx=3)
            ttk.Label(controls, text="Giá trị (độ):").pack(side="left", padx=3)
            ttk.Entry(controls, textvariable=value, width=9).pack(side="left", padx=3)
            for action in ("SET", "ADD", "SUB", "GET"):
                self.button(controls, action, lambda a=action, s=servo: self.edit(s, a)).pack(side="left", padx=3)
            self.button(controls, "Di chuyển tới vị trí", lambda s=servo: self.move(s)).pack(side="left", padx=8)

        ttk.Label(root, text=(
            "GET vị trí và REAL_ANGLE cùng trả góc gốc + offset. "
            "Đọc trường *_angle để xem góc gốc hoặc offset riêng.\n"
        ), wraplength=1030).grid(row=4, column=0, sticky="w", padx=12, pady=4)

        self.status = tk.StringVar(value=f"Chưa kết nối • Nguồn: {source}")
        ttk.Label(root, textvariable=self.status, wraplength=1050).grid(
            row=5, column=0, sticky="w", padx=10, pady=3)
        self.log = ScrolledText(root, height=8, state="disabled", font=("Courier", 9))
        self.log.grid(row=6, column=0, sticky="ew", padx=8, pady=5)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.update_buttons()
        root.after(50, self.drain)

    def button(self, parent, text, command):
        button = self.ttk.Button(parent, text=text, command=command)
        self.actions.append(button)
        return button

    def update_buttons(self):
        usable = self.link is not None and not self.link.failed and not self.busy
        for button in self.actions:
            button.configure(state="normal" if usable else "disabled")
        self.connect_button.configure(state="normal" if self.link is None and not self.busy else "disabled")
        self.disconnect_button.configure(state="normal" if self.link is not None and not self.busy else "disabled")

    def append_log(self, line):
        self.log.configure(state="normal")
        self.log.insert("end", time.strftime("%H:%M:%S ") + line + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 1000:
            self.log.delete("1.0", "200.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def job(self, operation):
        if self.busy:
            return
        self.busy = True
        self.update_buttons()

        def run():
            try:
                operation()
            except Exception as exc:
                self.events.put(("error", str(exc)))
            finally:
                if self.closed and self.link is not None:
                    self.link.serial.close()
                self.events.put(("idle", None))
        threading.Thread(target=run, daemon=True).start()

    def connect(self):
        try:
            port, baud, timeout = self.port.get().strip(), int(self.baud.get()), number(self.timeout.get())
            if not port or baud <= 0 or timeout <= 0:
                raise ValueError("Cổng, baud và timeout không hợp lệ")
        except ValueError as exc:
            self.status.set(str(exc))
            return

        def open_port():
            import serial
            uart = serial.Serial(port, baudrate=baud, timeout=0.1, write_timeout=1,
                                 xonxoff=False, rtscts=False, dsrdtr=False)
            self.link = CalibrationLink(uart, timeout, lambda d, line: self.events.put(("log", f"{d}: {line}")))
            self.events.put(("connected", f"Đã kết nối {port} @ {baud}. Chưa gửi lệnh."))
        self.job(open_port)

    def invalidate(self):
        self.live.clear()
        for tree in self.trees.values():
            for field in tree.get_children():
                tree.set(field, "uart", "Chưa đọc / cần đọc lại")

    def disconnect(self):
        if self.link:
            self.link.serial.close()
            self.link = None
        self.invalidate()
        self.status.set("Đã ngắt UART; đóng cổng không dừng chuyển động STM32.")
        self.update_buttons()

    def requests(self, commands, invalidate=False):
        # commands: (body, optional (servo_id, field)).
        if self.link is None or self.busy:
            return
        link = self.link
        try:
            # Validate the whole batch before sending any command, including
            # the actual sequence IDs and the firmware's 64-byte buffer limit.
            for offset, (body, _destination) in enumerate(commands):
                frame(link.next_id + offset, body)
        except ValueError as exc:
            self.status.set(str(exc))
            return
        if invalidate:
            self.invalidate()
        self.status.set(f"Đang xử lý {len(commands)} lệnh…")

        def execute():
            for body, destination in commands:
                value = link.request(body)
                if destination is not None and value is not None:
                    self.events.put(("value", (destination, value)))
            self.events.put(("status", "Hoàn tất các lệnh; xem TX/RX bên dưới."))
        self.job(execute)

    def selected(self):
        return self.servos[self.tabs.index(self.tabs.select())]

    def export_configuration(self):
        if self.link is None or self.busy or self.link.failed:
            return
        link = self.link
        self.status.set("Đang đọc REAL_ANGLE của 8 servo để lưu cấu hình…")

        def execute():
            export_servo_configuration(
                link, self.servos, EXPORT_PATH,
                lambda destination, value: self.events.put(("value", (destination, value))))
            self.events.put(("status", f"Đã lưu {EXPORT_PATH} — góc = REAL_ANGLE, offset = 0."))
        self.job(execute)

    @staticmethod
    def read_commands(servo):
        commands = [(f"CALIB SERVO GET {servo.id} {field}", (servo.id, field))
                    for field in ("channel", *servo.fields)]
        for position in POSITIONS[servo.kind]:
            commands.append((f"CALIB SERVO GET {servo.id} {position}", (servo.id, position)))
            commands.append((f"CALIB SERVO GET {servo.id} {position} REAL_ANGLE",
                             (servo.id, position + ":REAL_ANGLE")))
        return commands

    def refresh(self, all_servos=False):
        servos = self.servos if all_servos else [self.selected()]
        self.requests([command for servo in servos for command in self.read_commands(servo)])

    def edit(self, servo, action):
        try:
            position = self.position_vars[servo.id].get()
            body = servo_command(action, servo, position, self.value_vars[servo.id].get())
        except ValueError as exc:
            self.status.set(str(exc))
            return
        if action == "GET":
            self.requests([(body, (servo.id, position))])
        else:
            self.requests([(body, None)] + self.read_commands(servo), invalidate=True)

    def move(self, servo):
        position = self.position_vars[servo.id].get()
        self.requests([(f"CONTROL SERVO {servo.id} {position}", None)] +
                      self.read_commands(servo), invalidate=True)

    def drain(self):
        if self.closed:
            return
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.append_log(payload)
            elif kind == "value":
                destination, value = payload
                servo_id, field = destination
                self.live[destination] = value
                self.trees[servo_id].set(field, "uart", value)
            elif kind == "idle":
                self.busy = False
            elif kind == "connected":
                self.invalidate()
                self.status.set(payload)
            elif kind in {"error", "status"}:
                self.status.set(payload)
                self.append_log(("LỖI: " if kind == "error" else "") + payload)
        self.update_buttons()
        self.root.after(50, self.drain)

    def close(self):
        self.closed = True
        if self.link:
            self.link.cancel.set()
            if not self.busy:
                self.link.serial.close()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--servo-source", type=Path, default=DEFAULT_SOURCE,
                        help="Servo_Control.c chứa bảng khởi tạo servo")
    parser.add_argument("--port", default="/dev/serial0")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--check", action="store_true", help="Kiểm tra cấu trúc servo, không mở GUI/UART")
    args = parser.parse_args()
    try:
        servos = load_servos(args.servo_source)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    if args.check:
        for servo in servos:
            print(f"{servo.id}: {servo.name}, channel={servo.channel}, {servo.fields}")
        return
    import tkinter as tk
    root = tk.Tk()
    CalibrationApp(root, servos, args.servo_source, args.port, args.baudrate)
    root.mainloop()


if __name__ == "__main__":
    main()
