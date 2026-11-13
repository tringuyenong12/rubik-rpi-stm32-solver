"""Launch the camera scanner and arrow-guided Two-Phase desktop client."""
import argparse
import sys
from pathlib import Path
from threading import Thread

# Ensure rpi directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rpi"))

from twophase.vision2 import grab_colors
from twophase import vision2
import cv2


def main() -> None:
    """Input: camera/backend CLI options. Output: auto-scan client and live camera."""
    parser = argparse.ArgumentParser(description="Rubik camera scanner and Two-Phase client")
    parser.add_argument("--camera", type=int, default=1 if sys.platform == 'win32' else 0)
    parser.add_argument("--backend", choices=("auto", "dshow", "msmf"), default="auto")
    parser.add_argument("--show-masks", action="store_true", help="Show HSV tuning masks")
    args = parser.parse_args()
    backends = {"auto": None, "dshow": cv2.CAP_DSHOW, "msmf": cv2.CAP_MSMF}
    backend = backends[args.backend]
    if args.backend == "auto" and sys.platform == "win32":
        backend = cv2.CAP_DSHOW

    print(f"Starting camera {args.camera}. Hold each face still to capture it automatically.")
    thr = Thread(target=grab_colors, args=(args.camera, backend, args.show_masks), daemon=True)
    thr.start()

    print("Server address: localhost:8080. Guidance starts automatically after 6 validated faces.")
    try:
        import twophase.client_gui2
    finally:
        vision2.camera_stop.set()
        thr.join(timeout=2)


if __name__ == "__main__":
    main()
