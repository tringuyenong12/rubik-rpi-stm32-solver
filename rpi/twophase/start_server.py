import sys
from pathlib import Path

# Ensure parent directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import twophase.sockets as sockets


if __name__ == '__main__':  # file is executed
    if len(sys.argv) < 2:
        sys.argv.append(str(8080))  # Port 8080 default port
    if len(sys.argv) < 3:
        sys.argv.append(str(20))  # 20 moves default maximal return length of maneuver
    if len(sys.argv) < 4:
        sys.argv.append(str(3))  # 3 second default timeout for search
    print('startserver')
    sockets.server_start(sys.argv)
else:
    def start(port, maxmoves, timeout):
        sockets.server_start((-1, port, maxmoves, timeout))
