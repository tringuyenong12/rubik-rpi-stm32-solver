"""Launch the interactive webcam color calibration GUI from the integrated twophase package."""
import sys
from pathlib import Path
from threading import Thread

# Ensure rpi directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rpi"))

from twophase.vision2 import grab_colors


def main() -> None:
    print("Starting webcam color grabbing thread...")
    thr = Thread(target=grab_colors, args=(), daemon=True)
    thr.start()

    print("Opening interactive Rubik GUI editor and webcam tuner...")
    import twophase.client_gui2


if __name__ == "__main__":
    main()
