
"""Interactive UART terminal for Raspberry Pi <-> STM32.

Run:
    python3 tests/test_uart_pi.py --port /dev/serial0 --baudrate 115200
"""

import argparse
import serial
import time

COMMAND_TIMEOUT = 20.0  # seconds

# def send_command(uart: serial.Serial, command: str) -> None:
#     # Get command ID: "#1 RUBIK MOVE L" -> "#1"
#     command_id = command.split(maxsplit=1)[0]
#     expected_id = ">" + command_id

#     # Clear any stale input before sending
#     uart.reset_input_buffer()

#     # Send command to STM32
#     uart.write((command + "\n").encode("utf-8"))
#     uart.flush()
#     print(f"[TX] {command}")

#     # Wait for DONE or ERR with matching command ID
#     while True:
#         response = uart.readline()

#         if not response:
#             continue

#         text = response.decode(
#             "utf-8", errors="replace"
#         ).strip()

#         if not text:
#             continue

#         # Display all STM32 responses
#         print(f"[RX] {text}")

#         parts = text.split(maxsplit=2)

#         if len(parts) < 2:
#             continue

#         response_id = parts[0]
#         status = parts[1]

#         if response_id != expected_id:
#             continue

#         if status == "DONE":
#             print("[INFO] Command completed.\n")
#             return

#         if status == "ERR":
#             print("[ERROR] STM32 reported an error.\n")
#             return










def send_command(uart: serial.Serial, command: str) -> None:
    # Get command ID: "#2 RUBIK MOVE L" -> "#2"
    command_id = command.split(maxsplit=1)[0]
    expected_id = f">{command_id}"

    # Send command to STM32
    uart.write((command + "\n").encode("utf-8"))
    uart.flush()

    print(f"[TX] {command}")

    # Start timeout timer
    start_time = time.monotonic()

    # Wait until DONE, ERR or timeout
    while True:

        # Check timeout
        if time.monotonic() - start_time >= COMMAND_TIMEOUT:
            print(
                f"[ERROR] NO_RESPONSE: "
                f"{command_id} timeout after {COMMAND_TIMEOUT:g}s\n"
            )
            return

        response = uart.readline()

        if not response:
            continue

        text = response.decode(
            "utf-8", errors="replace"
        ).strip()

        if not text:
            continue

        # Display all responses from STM32
        print(f"[RX] {text}")

        # Split response into ID and content
        parts = text.split(maxsplit=1)

        if len(parts) < 2:
            continue

        response_id, content = parts

        # Ignore responses with different command ID
        if response_id != expected_id:
            continue

        # Check DONE
        if content == "DONE":
            print("[INFO] Command completed.\n")
            return

        # Check ERR
        if "ERR" in content:
            print(f"[ERROR] Command failed: {content}\n")
            return

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Interactive STM32 UART terminal"
    )

    parser.add_argument(
        "--port",
        default="/dev/serial0",
        help="UART port"
    )

    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="UART baudrate"
    )

    args = parser.parse_args()

    try:
        with serial.Serial(
            port=args.port,
            baudrate=args.baudrate,
            timeout=0.5
        ) as uart:

            print("STM32 UART Terminal")
            print(f"Port: {args.port}")
            print(f"Baudrate: {args.baudrate}")
            print("Type 'exit' to quit.\n")

            # Test connection
            send_command(uart, "#1 RUBIK PING")

            while True:
                try:
                    command = input("UART> ").strip()

                    if command.lower() in ("exit", "quit"):
                        break

                    if not command:
                        continue

                    send_command(uart, command)

                except (KeyboardInterrupt, EOFError):
                    print("\nExiting...")
                    break

    except serial.SerialException as e:
        print(f"[UART ERROR] {e}")


if __name__ == "__main__":
    main()
