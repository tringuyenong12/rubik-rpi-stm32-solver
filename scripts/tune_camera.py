"""Collect repeatable exposure trials without issuing robot movement commands."""
import argparse
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rpi'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', type=int, default=1)
    parser.add_argument('--output', type=Path, default=Path('artifacts/camera_tuning'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY)
    if not cap.isOpened():
        raise RuntimeError('Close the scanner before collecting camera trials')
    properties = ('EXPOSURE', 'AUTO_EXPOSURE', 'GAIN', 'AUTO_WB', 'WB_TEMPERATURE')
    original = {name: cap.get(getattr(cv2, 'CAP_PROP_' + name)) for name in properties}
    report = {'original': original, 'trials': []}
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        warmup = time.monotonic() + 2
        while time.monotonic() < warmup:
            cap.read()
        for exposure, gain in ((-6, 20), (-7, 20), (-8, 20), (-6, 0), (-7, 0)):
            accepted = {
                'AUTO_EXPOSURE': cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, .25),
                'EXPOSURE': cap.set(cv2.CAP_PROP_EXPOSURE, exposure),
                'GAIN': cap.set(cv2.CAP_PROP_GAIN, gain),
            }
            settle = time.monotonic() + 1
            while time.monotonic() < settle:
                cap.read()
            frames = []
            for _ in range(24):
                ok, frame = cap.read()
                if ok:
                    frames.append(frame)
            name = f'exposure_{exposure}_gain_{gain}'
            if not frames:
                raise RuntimeError('Camera stopped producing frames')
            np.savez_compressed(args.output / (name + '.npz'), frames=np.asarray(frames))
            cv2.imwrite(str(args.output / (name + '.jpg')), frames[-1])
            record = {'name': name, 'frames': len(frames), 'accepted': accepted,
                      'readback': {key: cap.get(getattr(cv2, 'CAP_PROP_' + key)) for key in properties}}
            report['trials'].append(record)
            print(json.dumps(record), flush=True)
    finally:
        # Trials do not leave a losing camera configuration active.
        for key in ('EXPOSURE', 'GAIN', 'WB_TEMPERATURE', 'AUTO_WB', 'AUTO_EXPOSURE'):
            if original[key] >= 0 or key == 'EXPOSURE':
                cap.set(getattr(cv2, 'CAP_PROP_' + key), original[key])
        cap.release()
        (args.output / 'trials.json').write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
