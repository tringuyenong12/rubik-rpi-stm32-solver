"""Send Rubik face moves through the existing UART_Command layer.

Import with ``from Rubik_Cube.Rubik_Move import move_Front, U, R_``
when running from rpi/. Importing this module does not open the UART port.
Each call blocks until UART_Command returns and propagates its bool result.
The suffix ``_`` denotes the inverse move, e.g. F_ corresponds to F'.
"""

from .UART_Command import UART_Command


def move(face: str) -> bool:
    """Send one of F/R/B/L/U/D, optionally followed by _ or apostrophe.

    Invalid moves raise ValueError before sending anything. UART_Command
    supplies the command ID and newline; do not add them here.
    """
    if not isinstance(face, str):
        raise ValueError("Move must be a string such as F, U_ or R'")
    token = face.strip().upper()
    if token.endswith("'"):
        token = token[:-1] + "_"
    if token not in {"F", "R", "B", "L", "U", "D",
                     "F_", "R_", "B_", "L_", "U_", "D_"}:
        raise ValueError(f"Unsupported Rubik move: {face!r}")
    return UART_Command.Send_Command_to_STM32(f"RUBIK MOVE {token}")


def move_Front() -> bool:
    """Send RUBIK MOVE F."""
    return move("F")


def move_Front_() -> bool:
    """Send RUBIK MOVE F_ (inverse Front)."""
    return move("F_")


def move_Right() -> bool:
    """Send RUBIK MOVE R."""
    return move("R")


def move_Right_() -> bool:
    """Send RUBIK MOVE R_ (inverse Right)."""
    return move("R_")


def move_Back() -> bool:
    """Send RUBIK MOVE B."""
    return move("B")


def move_Back_() -> bool:
    """Send RUBIK MOVE B_ (inverse Back)."""
    return move("B_")


def move_Left() -> bool:
    """Send RUBIK MOVE L."""
    return move("L")


def move_Left_() -> bool:
    """Send RUBIK MOVE L_ (inverse Left)."""
    return move("L_")


def move_Up() -> bool:
    """Send RUBIK MOVE U."""
    return move("U")


def move_Up_() -> bool:
    """Send RUBIK MOVE U_ (inverse Up)."""
    return move("U_")


def move_Down() -> bool:
    """Send RUBIK MOVE D."""
    return move("D")


def move_Down_() -> bool:
    """Send RUBIK MOVE D_ (inverse Down)."""
    return move("D_")

def move_LR() -> bool:
    """Send RUBIK MOVE LR (Left and Right together)."""
    return move("LR")

def move_LR_() -> bool:
    """Send RUBIK MOVE LR_ (inverse Left and Right together)."""
    return move("LR_")

def move_L_R() -> bool:
    """Send RUBIK MOVE L'R' (inverse Left and Right together)."""
    return move("L_R")

def move_L_R_() -> bool:
    """Send RUBIK MOVE L'R'_ (inverse Left and Right together)."""
    return move("L_R_")

def move_UD() -> bool:
    """Send RUBIK MOVE UD (Up and Down together)."""
    return move("UD")

def move_UD_() -> bool:
    """Send RUBIK MOVE UD_ (inverse Up and Down together)."""
    return move("UD_")

def move_U_D() -> bool:
    """Send RUBIK MOVE U'D' (inverse Up and Down together)."""
    return move("U_D")

def move_U_D_() -> bool:
    """Send RUBIK MOVE U'D'_ (inverse Up and Down together)."""
    return move("U_D_")







# Short cube notation, with and without the move_ prefix.
F = move_F = move_Front
F_ = move_F_ = move_Front_
R = move_R = move_Right
R_ = move_R_ = move_Right_
B = move_B = move_Back
B_ = move_B_ = move_Back_
L = move_L = move_Left
L_ = move_L_ = move_Left_
U = move_U = move_Up
U_ = move_U_ = move_Up_
D = move_D = move_Down
D_ = move_D_ = move_Down_
