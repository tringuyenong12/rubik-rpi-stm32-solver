"""Run the local web app; input: CLI flags, output: localhost HTTP service."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rpi"))

from rubik_robot.web.studio_server import main


if __name__ == "__main__":
    main()
