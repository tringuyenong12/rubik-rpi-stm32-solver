
"""
UART Command Module
Raspberry Pi <-> STM32

Usage:
    from UART_Command import Send_Command_to_STM32

    Send_Command_to_STM32("RUBIK MOVE L")
"""

import time
import threading
import serial

# ==============================
# UART CONFIGURATION
# ==============================

UART_PORT = "/dev/serial0"
UART_BAUDRATE = 115200

UART_READ_TIMEOUT = 0.1
UART_OK_TIMEOUT = 1.0

# ==============================
# GLOBAL VARIABLES
# ==============================

_uart = None
_command_id = 0

# Prevent simultaneous UART commands
_uart_lock = threading.Lock()


# ==============================
# UART INITIALIZATION
# ==============================

def UART_Init():
    global _uart

    if _uart is not None and _uart.is_open:
        return _uart

    _uart = serial.Serial(
        port=UART_PORT,
        baudrate=UART_BAUDRATE,
        timeout=UART_READ_TIMEOUT,
        write_timeout=1.0
    )

    print(f"[UART] Connected: {UART_PORT}")
    return _uart


# ==============================
# UART CLOSE
# ==============================

def UART_Close():
    global _uart

    with _uart_lock:
        if _uart is not None:
            if _uart.is_open:
                _uart.close()

            _uart = None
            print("[UART] Connection closed")


# ==============================
# SEND COMMAND TO STM32
# ==============================

def Send_Command_to_STM32(command: str) -> bool:
    global _command_id

    if not command or not command.strip():
        print("[ERROR] Empty command")
        return False

    with _uart_lock:
        try:
            uart = UART_Init()

            # Automatically generate command ID
            _command_id += 1
            command_id = _command_id

            expected_id = f">#{command_id}"

            # Generate UART command
            full_command = f"#{command_id} {command.strip()}"

            # Send command
            uart.write(
                (full_command + "\n").encode("utf-8")
            )
            uart.flush()

            print(f"[TX] {full_command}")

            # Start OK timeout
            start_time = time.monotonic()
            ok_received = False

            # Wait for OK, DONE or ERR
            while True:

                # Check 1-second OK timeout
                if not ok_received:
                    if (
                        time.monotonic() - start_time
                        >= UART_OK_TIMEOUT
                    ):
                        print(
                            f"[ERROR] NO_RESPONSE: "
                            f"#{command_id} OK timeout\n"
                        )
                        return False

                response = uart.readline()

                if not response:
                    continue

                text = response.decode(
                    "utf-8",
                    errors="replace"
                ).strip()

                if not text:
                    continue

                # Display all STM32 responses
                print(f"[RX] {text}")

                # Parse ID and response content
                parts = text.split(maxsplit=1)

                if len(parts) < 2:
                    continue

                response_id, content = parts

                # Ignore other command IDs
                if response_id != expected_id:
                    continue

                # Check ERR
                if "ERR" in content:
                    print(
                        f"[ERROR] Command failed: "
                        f"{content}\n"
                    )
                    return False

                # Check OK
                if content == "OK":
                    ok_received = True
                    print("[INFO] Command accepted")
                    continue

                # Check DONE
                if content == "DONE" and ok_received:
                    print(
                        "[INFO] Command completed.\n"
                    )
                    return True

        except (
            serial.SerialException,
            serial.SerialTimeoutException,
            OSError
        ) as e:
            print(f"[UART ERROR] {e}")

            # Reset port after communication error
            global _uart
            if _uart is not None:
                try:
                    _uart.close()
                except Exception:
                    pass

                _uart = None

            return False
