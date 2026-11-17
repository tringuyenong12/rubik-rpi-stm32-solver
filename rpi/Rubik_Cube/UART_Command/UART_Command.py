"""Public UART API shared by face helpers, terminal and solver."""
import threading
import serial

if __package__:
    from .session import UARTSession
else:  # Existing test_UART_Command.py terminal launched directly.
    from session import UARTSession

UART_PORT = "/dev/serial0"
UART_BAUDRATE = 115200
UART_READ_TIMEOUT = 0.1
UART_OK_TIMEOUT = 1.0
UART_DONE_TIMEOUT = 30.0
_default_session = None
_default_lock = threading.Lock()


def _get_default():
    global _default_session
    with _default_lock:
        if _default_session is None:
            _default_session = UARTSession(UART_PORT, UART_BAUDRATE,
                                           UART_DONE_TIMEOUT, UART_OK_TIMEOUT)
        return _default_session


def UART_Init():
    return _get_default().open()


def UART_Close():
    global _default_session
    with _default_lock:
        if _default_session is not None:
            _default_session.close()
            _default_session = None


def Send_Command_to_STM32(command: str, *, session=None) -> bool:
    session = _get_default() if session is None else session
    try:
        session.request(command)
        return True
    except (OSError, RuntimeError, ValueError, serial.SerialException) as error:
        session.last_error = error
        print(f"[UART ERROR] {error}")
        return False
