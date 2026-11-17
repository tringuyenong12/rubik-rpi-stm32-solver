"""Send Rubik face moves through the existing UART_Command layer.

Import with ``from Rubik_Cube.motion.motion import move_Front, U, R_``
when running from rpi/. Importing this module does not open the UART port.
Each call blocks until UART_Command returns and propagates its bool result.
The suffix ``_`` denotes the inverse move, e.g. F_ corresponds to F'.
"""

from ..UART_Command import UART_Command


def move(face: str, *, session=None) -> bool:
    """Send a face or firmware LR/FB pair, with independent inverse suffixes.

    Invalid moves raise ValueError before sending anything. UART_Command
    supplies the command ID and newline; do not add them here.
    """
    if not isinstance(face, str):
        raise ValueError("Move must be a string such as F, U_ or R'")
    token = face.strip().upper()
    token = token.replace("'", "_")
    if token not in {"F", "R", "B", "L", "U", "D",
                     "F_", "R_", "B_", "L_", "U_", "D_",
                     "LR", "LR_", "L_R", "L_R_",
                     "FB", "FB_", "F_B", "F_B_"}:
        raise ValueError(f"Unsupported Rubik move: {face!r}")
    return UART_Command.Send_Command_to_STM32(f"RUBIK MOVE {token}", session=session)


def move_Front(*, session=None) -> bool:
    """Send RUBIK MOVE F."""
    return move("F", session=session)


def move_Front_(*, session=None) -> bool:
    """Send RUBIK MOVE F_ (inverse Front)."""
    return move("F_", session=session)


def move_Right(*, session=None) -> bool:
    """Send RUBIK MOVE R."""
    return move("R", session=session)


def move_Right_(*, session=None) -> bool:
    """Send RUBIK MOVE R_ (inverse Right)."""
    return move("R_", session=session)


def move_Back(*, session=None) -> bool:
    """Send RUBIK MOVE B."""
    return move("B", session=session)


def move_Back_(*, session=None) -> bool:
    """Send RUBIK MOVE B_ (inverse Back)."""
    return move("B_", session=session)


def move_Left(*, session=None) -> bool:
    """Send RUBIK MOVE L."""
    return move("L", session=session)


def move_Left_(*, session=None) -> bool:
    """Send RUBIK MOVE L_ (inverse Left)."""
    return move("L_", session=session)


def move_Up(*, session=None) -> bool:
    """Send RUBIK MOVE U."""
    return move("U", session=session)


def move_Up_(*, session=None) -> bool:
    """Send RUBIK MOVE U_ (inverse Up)."""
    return move("U_", session=session)


def move_Down(*, session=None) -> bool:
    """Send RUBIK MOVE D."""
    return move("D", session=session)


def move_Down_(*, session=None) -> bool:
    """Send RUBIK MOVE D_ (inverse Down)."""
    return move("D_", session=session)

def move_LR(*, session=None) -> bool:
    """Send RUBIK MOVE LR (Left and Right together)."""
    return move("LR", session=session)

def move_LR_(*, session=None) -> bool:
    """Send RUBIK MOVE LR_ (Left and inverse Right together)."""
    return move("LR_", session=session)

def move_L_R(*, session=None) -> bool:
    """Send RUBIK MOVE L_R (inverse Left and Right together)."""
    return move("L_R", session=session)

def move_L_R_(*, session=None) -> bool:
    """Send RUBIK MOVE L_R_ (both faces inverse)."""
    return move("L_R_", session=session)

def move_FB(*, session=None) -> bool:
    """Send RUBIK MOVE FB (Front and Back together)."""
    return move("FB", session=session)

def move_FB_(*, session=None) -> bool:
    """Send RUBIK MOVE FB_ (inverse Front and Back together)."""
    return move("FB_", session=session)

def move_F_B(*, session=None) -> bool:
    """Send RUBIK MOVE F_B (inverse Front and Back together)."""
    return move("F_B", session=session)

def move_F_B_(*, session=None) -> bool:
    """Send RUBIK MOVE F_B_ (inverse Front and Back together)."""
    return move("F_B_", session=session)







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
