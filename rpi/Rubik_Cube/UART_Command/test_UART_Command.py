
# Test script for UART_Command module
# Run: python3 Rubik_Cube/UART_Command/test_UART_Command.py

from UART_Command import (
    Send_Command_to_STM32,
    UART_Close
)


def main():
    print("===== STM32 UART COMMAND TERMINAL =====")
    print("Enter UART commands without #ID")
    print("Example: CONTROL SERVO 7 CLAMP")
    print("Type 'exit' or 'quit' to stop.\n")

    try:
        while True:
            command = input("UART> ").strip()

            # Exit program
            if command.lower() in ("exit", "quit"):
                break

            # Ignore empty commands
            if not command:
                continue

            # Send command to STM32
            success = Send_Command_to_STM32(command)

            if not success:
                print("[TEST] Command failed.\n")

    except (KeyboardInterrupt, EOFError):
        print("\n[TEST] Exiting...")

    finally:
        UART_Close()




if __name__ == "__main__":
    main()


# # Run this script to test sending commands to the STM32 via UART.
# # Run: python3 Rubik_Cube/UART_Command/test_UART_Command.py

# from UART_Command import (
#     Send_Command_to_STM32,
#     UART_Close
# )

# try:
#     # Send_Command_to_STM32("CONTROL SERVO 7 CLAMP")

#     Send_Command_to_STM32("RUBIK PING")

#     Send_Command_to_STM32("RUBIK MOVE L")

#     Send_Command_to_STM32("RUBIK MOVE R")

#     Send_Command_to_STM32("RUBIK MOVE F")

#     # Send_Command_to_STM32("RUBIK MOVE B")

#     Send_Command_to_STM32("RUBIK MOVE U")

#     Send_Command_to_STM32("RUBIK MOVE D")


#     Send_Command_to_STM32("RUBIK PING")

#     Send_Command_to_STM32("RUBIK MOVE L_")

#     Send_Command_to_STM32("RUBIK MOVE R_")

#     Send_Command_to_STM32("RUBIK MOVE F_")

#     # Send_Command_to_STM32("RUBIK MOVE B_")

#     Send_Command_to_STM32("RUBIK MOVE U_")

#     Send_Command_to_STM32("RUBIK MOVE D_")




# finally:
#     UART_Close()