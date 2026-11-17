"""Replay independently labelled camera holds and report recognition accuracy.

Manifest format: {"directory": "path", "holds": [{"start": 0, "end": 20,
"expected": [["red", ...], ...]}]}. Only label stationary, unobstructed frames.
"""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rpi'))
from rubik_robot.vision.camera_settings import load_vision_profile
from rubik_robot.vision.roi import CameraROI
from twophase import vision2


def evaluate(manifest, camera_id=1):
    load_vision_profile(camera_id)
    roi = CameraROI()
    roi.load(camera_id)
    directory = Path(manifest['directory'])
    total, detected, exact, stickers = 0, 0, 0, 0
    holds = []
    for hold in manifest['holds']:
        expected = np.asarray(hold['expected'])
        if expected.shape != (3, 3):
            raise ValueError('Each hold needs nine independently verified colors')
        counts = {'frames': 0, 'detected': 0, 'exact': 0, 'correct_stickers': 0}
        errors = []
        for index in range(hold['start'], hold['end'] + 1):
            name = f'frame_{index:04d}.png'
            frame = cv2.imread(str(directory / name))
            if frame is None:
                raise FileNotFoundError(directory / name)
            _, colors = vision2.detect_face(frame, roi.selection(frame.shape))
            counts['frames'] += 1
            if colors:
                counts['detected'] += 1
                counts['correct_stickers'] += int(np.sum(np.asarray(colors) == expected))
            if colors == hold['expected']:
                counts['exact'] += 1
            else:
                errors.append({'frame': name, 'colors': colors})
        holds.append({'name': hold.get('name', ''), **counts, 'errors': errors})
        total += counts['frames']
        detected += counts['detected']
        exact += counts['exact']
        stickers += counts['correct_stickers']
    return {'frames': total, 'detected': detected, 'exact': exact,
            'correct_stickers': stickers, 'total_stickers': total * 9, 'holds': holds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--camera', type=int, default=1)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = evaluate(json.loads(args.manifest.read_text(encoding='utf-8')), args.camera)
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text, encoding='utf-8')


if __name__ == '__main__':
    main()
