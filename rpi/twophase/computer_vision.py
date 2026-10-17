import sys
from pathlib import Path
from threading import Thread

# Luon them thu muc cha (rpi) vao sys.path de chay duoc tu moi thu muc
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from twophase.vision2 import grab_colors

# daemon=True giup tat luong camera tu dong khi tat GUI
thr = Thread(target=grab_colors, args=(), daemon=True)
thr.start()

import twophase.client_gui2
