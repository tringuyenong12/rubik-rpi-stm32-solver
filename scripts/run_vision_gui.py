"""Launch camera scanning with formula output and separate illustrated move cards."""
import argparse
import json
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
    parser.add_argument('--diagnostics', type=Path, help='Record up to 480 raw frames and detection results')
    parser.add_argument('--restore-solution', type=Path, help='Reopen a saved cube/solution JSON without rescanning')
    parser.add_argument('--performance', type=Path, help='Save timing and recognition metrics when the camera closes')
    args = parser.parse_args()
    if args.performance:
        from rubik_robot.vision.performance import CameraPerformance
        vision2.performance_recorder = CameraPerformance(args.performance)
    if args.restore_solution:
        from rubik_robot.vision.move_instructions import SolutionWalkthrough
        from twophase import vision_params
        try:
            saved = json.loads(args.restore_solution.read_text(encoding='utf-8'))
            checked = SolutionWalkthrough()
            checked.load(saved['cube'], saved['solution'])
            vision_params.initial_solution = {'cube': checked.cube, 'solution': checked.solution}
        except (OSError, ValueError, KeyError, TypeError) as error:
            parser.error(f'Cannot restore solution: {error}')
    from rubik_robot.vision.camera_settings import load_vision_profile
    load_vision_profile(args.camera)
    if args.diagnostics:
        from rubik_robot.vision.diagnostics import FrameRecorder
        vision2.diagnostic_recorder = FrameRecorder(args.diagnostics)
    backends = {"auto": None, "dshow": cv2.CAP_DSHOW, "msmf": cv2.CAP_MSMF}
    backend = backends[args.backend]
    if args.backend == "auto" and sys.platform == "win32":
        backend = cv2.CAP_DSHOW

    print(f"Starting camera {args.camera}. Hold each face still to capture it automatically.")
    thr = Thread(target=grab_colors, args=(args.camera, backend, args.show_masks), daemon=True)
    vision2.camera_options = (args.camera, backend, args.show_masks)
    vision2.camera_thread = thr
    thr.start()

    print("Solver: localhost:8080 with local fallback. After 6 faces, open the formula and illustrated move cards.")
    try:
        import twophase.client_gui2
    finally:
        vision2.camera_stop.set()
        # Performance snapshots are written only after preview stops.
        vision2.camera_thread.join(timeout=10 if vision2.performance_recorder is not None else 2)


if __name__ == "__main__":
    main()
