"""Launch the webcam tuner and add a reproducible Random scramble action.

The upstream ``twophase.client_gui2`` module starts Tk's main loop at import
time.  To keep that vendor module untouched, this launcher replaces only its
Random button command while the GUI is being constructed.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path
from threading import Thread

# Ensure rpi directory is in sys.path.
RPI_DIR = Path(__file__).resolve().parent.parent / "rpi"
if str(RPI_DIR) not in sys.path:
    sys.path.insert(0, str(RPI_DIR))

from twophase import cubie
from twophase.vision2 import grab_colors


FACE_ORDER = "URFDLB"
MODIFIERS = ("", "'", "2")
OPPOSITE_FACE = {
    "U": "D", "D": "U",
    "R": "L", "L": "R",
    "F": "B", "B": "F",
}

# Match the byte values used by the STM32 face-turn callback.
STM32_MOVE_CODES: dict[tuple[str, int], int] = {
    ("F", 1): 1, ("F", -1): 2, ("F", 2): 3,
    ("B", 1): 4, ("B", -1): 5, ("B", 2): 6,
    ("L", 1): 7, ("L", -1): 8, ("L", 2): 9,
    ("R", 1): 10, ("R", -1): 11, ("R", 2): 12,
    ("U", 1): 13, ("U", -1): 14, ("U", 2): 15,
    ("D", 1): 16, ("D", -1): 17, ("D", 2): 18,
}

# Random length within each range keeps repeated clicks varied while retaining
# a clear difficulty level for users and expected STM32 execution time.
SCRAMBLE_LEVELS: dict[str, tuple[int, int]] = {
    "Easy": (5, 8),
    "Medium": (12, 18),
    "Hard": (20, 25),
}


def generate_scramble(length: int = 20) -> list[str]:
    """Generate a normal 3x3 scramble with no redundant adjacent moves."""
    if length <= 0:
        raise ValueError("Scramble length must be positive")

    moves: list[str] = []
    previous_face = ""
    before_previous_face = ""
    for _ in range(length):
        candidates = [face for face in FACE_ORDER if face != previous_face]
        if before_previous_face == OPPOSITE_FACE.get(previous_face):
            candidates = [face for face in candidates if face != before_previous_face]

        face = random.choice(candidates)
        moves.append(face + random.choice(MODIFIERS))
        before_previous_face, previous_face = previous_face, face
    return moves


def _move_turns(move: str) -> int:
    if move.endswith("'"):
        return -1
    if move.endswith("2"):
        return 2
    return 1


def scramble_to_facelets(moves: list[str]) -> str:
    """Apply moves with the bundled twophase model and return URFDLB facelets."""
    cube = cubie.CubieCube()
    for move in moves:
        face = move[0]
        turns = _move_turns(move)
        repeats = 3 if turns == -1 else turns
        basic_move = cubie.basicMoveCube[FACE_ORDER.index(face)]
        for _ in range(repeats):
            cube.multiply(basic_move)
    return cube.to_facelet_cube().to_string()


def stm32_steps(moves: list[str]) -> list[str]:
    """Return readable movement steps with the exact byte sent to STM32."""
    steps: list[str] = []
    for index, move in enumerate(moves, start=1):
        face = move[0]
        turns = _move_turns(move)
        code = STM32_MOVE_CODES[(face, turns)]
        steps.append(f"{index:02d}. {move:<2} -> UART byte {code:3d} (0x{code:02X})")
    return steps


def _show_scramble_in_gui(level: str = "Medium") -> None:
    """Show a level-specific, reproducible scramble and its UART steps."""
    gui = sys.modules.get("twophase.client_gui2")
    if gui is None:
        raise RuntimeError("The GUI is not ready")

    try:
        minimum_moves, maximum_moves = SCRAMBLE_LEVELS[level]
    except KeyError as exc:
        raise ValueError(f"Unknown scramble level: {level}") from exc

    moves = generate_scramble(random.randint(minimum_moves, maximum_moves))
    facelets = scramble_to_facelets(moves)
    color_by_facelet = dict(zip(FACE_ORDER, gui.cols))

    # client_gui2 stores faces in URFDLB order, exactly like FaceCube.to_string.
    for face_index in range(6):
        for row in range(3):
            for column in range(3):
                sticker_index = face_index * 9 + row * 3 + column
                gui.canvas.itemconfig(
                    gui.facelet_id[face_index][row][column],
                    fill=color_by_facelet[facelets[sticker_index]],
                )

    steps = stm32_steps(moves)
    text = (
        f"Scramble {level} ({len(moves)} moves):\n"
        + " ".join(moves)
        + "\n\nSTM32 bytes:\n"
        + " ".join(str(STM32_MOVE_CODES[(move[0], _move_turns(move))]) for move in moves)
        + "\n\n54 facelets:\n"
        + facelets
    )
    print("\n" + text)
    print("\nDetailed STM32 steps:\n" + "\n".join(steps))

    gui.display.delete("1.0", "end")
    gui.display.insert("end", text)


def _hide_level_buttons(gui) -> None:
    """Remove the embedded difficulty buttons from the expanded Canvas."""
    for window in getattr(gui, "_scramble_level_windows", ()):
        gui.canvas.delete(window)
    for button in getattr(gui, "_scramble_level_buttons", ()):
        button.destroy()
    gui._scramble_level_buttons = ()
    gui._scramble_level_windows = ()


def _toggle_level_buttons() -> None:
    """Show or hide Easy, Medium, Hard horizontally below Scramble."""
    gui = sys.modules.get("twophase.client_gui2")
    if gui is None:
        raise RuntimeError("The GUI is not ready")

    if getattr(gui, "_scramble_level_buttons", ()):
        _hide_level_buttons(gui)
        return

    import tkinter

    buttons = []
    windows = []
    # The Canvas is widened by the construction hook below.  Start at the
    # left edge of Scramble, leaving room for all three horizontal buttons.
    start_x = 10 + 10.5 * gui.width
    button_y = 10 + 9.15 * gui.width
    spacing = 1.8 * gui.width

    for index, level in enumerate(("Easy", "Medium", "Hard")):
        def select_level(selected_level: str = level) -> None:
            _show_scramble_in_gui(selected_level)
            _hide_level_buttons(gui)

        button = tkinter.Button(
            gui.root,
            text=level,
            height=1,
            width=10,
            relief=tkinter.RAISED,
            command=select_level,
        )
        window = gui.canvas.create_window(
            start_x + index * spacing,
            button_y,
            anchor="nw",
            window=button,
        )
        buttons.append(button)
        windows.append(window)

    gui._scramble_level_buttons = tuple(buttons)
    gui._scramble_level_windows = tuple(windows)


def _replace_random_button() -> None:
    """Install the Trộn callback before client_gui2 imports ``Button``."""
    import tkinter

    original_button = tkinter.Button
    original_canvas = tkinter.Canvas

    def button_with_scramble(*args, **kwargs):
        if kwargs.get("text") == "Random":
            # The former Random button becomes a menu for the three levels.
            kwargs = {
                **kwargs,
                "text": "Scramble",
                "command": _toggle_level_buttons,
            }
        return original_button(*args, **kwargs)

    def expanded_canvas(*args, **kwargs):
        """Make room below and to the right of the original controls."""
        requested_width = kwargs.get("width")
        requested_height = kwargs.get("height")
        if isinstance(requested_width, (int, float)) and isinstance(
            requested_height, (int, float)
        ):
            # client_gui2 uses 12 facelet widths horizontally and 9 vertically.
            facelet_width = max(1, round((requested_width - 20) / 12))
            kwargs = {
                **kwargs,
                "width": requested_width + 5 * facelet_width,
                "height": requested_height + 2 * facelet_width,
            }
        return original_canvas(*args, **kwargs)

    tkinter.Button = button_with_scramble
    tkinter.Canvas = expanded_canvas


def main() -> None:
    print("Starting webcam color grabbing thread...")
    Thread(target=grab_colors, daemon=True).start()

    # client_gui2 enters mainloop during import, so the hook has to precede it.
    _replace_random_button()
    print("Opening GUI. Click Scramble, then choose Easy/Medium/Hard.")
    import twophase.client_gui2  # noqa: F401


if __name__ == "__main__":
    main()
