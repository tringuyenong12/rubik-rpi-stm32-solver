"""Measure real camera, detection and preview latency without moving the robot."""
import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'rpi'))
from twophase import vision2
from rubik_robot.vision.camera_settings import apply_camera_profile, configure_camera_runtime, CAMERA_WARMUP_SECONDS
from rubik_robot.vision.face_scanner import new_camera_scanner
from rubik_robot.vision.scan_preview import StableScanPreview


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera', type=int, default=1)
    parser.add_argument('--seconds', type=float, default=10)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int)
    args = parser.parse_args()
    if args.threads is not None:
        cv2.setNumThreads(args.threads)
    else:
        configure_camera_runtime()
    cap = cv2.VideoCapture(args.camera, cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY)
    if not cap.isOpened():
        raise RuntimeError('Close the existing camera session before benchmarking')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scanner = new_camera_scanner()
    stable_preview = StableScanPreview()
    vision2.camera_roi.load(args.camera)
    rows, frames, frame_times = [], [], []
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        settings = apply_camera_profile(cap, args.camera)
        warm = perf_counter() + CAMERA_WARMUP_SECONDS
        while perf_counter() < warm:
            cap.read()
        started = perf_counter()
        while perf_counter() - started < args.seconds:
            t0 = perf_counter()
            ok, frame = cap.read()
            t1 = perf_counter()
            if not ok or frame is None:
                raise RuntimeError('Camera stopped producing frames')
            if frame.shape[1] > 640:
                frame = cv2.resize(frame, (640, round(frame.shape[0]*640/frame.shape[1])))
            samples, colors = vision2.detect_face(frame, vision2.camera_roi.selection(frame.shape), include_masks=False)
            preview_colors, preview_boxes = stable_preview.update(frame, colors, vision2.face_boxes,
                                                                  vision2.camera_roi.selection(frame.shape), now=t1)
            scanner.update(colors, now=t1, hsv_grid=samples, displayed_grid=preview_colors)
            t2 = perf_counter()
            preview = vision2.draw_scan_overlay(vision2.camera_roi.draw(frame.copy()), preview_colors,
                                                scanner.snapshot(), boxes_override=preview_boxes)
            t3 = perf_counter()
            cv2.imshow('Rubik Camera Performance', preview)
            key = cv2.waitKey(1) & 255
            t4 = perf_counter()
            rows.append({'time': t4-started, 'capture_ms': (t1-t0)*1000,
                         'detect_ms': (t2-t1)*1000, 'draw_ms': (t3-t2)*1000,
                         'display_ms': (t4-t3)*1000, 'total_ms': (t4-t0)*1000,
                         'colors': colors})
            if len(rows) % 3 == 0 and len(frames) < 240:
                frames.append(frame.copy())
                frame_times.append(t4-started)
            if key in (27, ord('q')):
                break
        elapsed = perf_counter() - started
        summary = {'frames': len(rows), 'seconds': elapsed, 'fps': len(rows)/elapsed,
                   'opencv_threads': cv2.getNumThreads(), 'camera_settings': settings,
                   'complete_grids': sum(bool(row['colors']) for row in rows),
                   'saved_centers': list(scanner.snapshot()['faces'])}
        for name in ('capture_ms', 'detect_ms', 'draw_ms', 'display_ms', 'total_ms'):
            values = [row[name] for row in rows]
            summary[name] = {'median': float(np.median(values)), 'p95': float(np.percentile(values, 95)),
                             'max': max(values)}
        summary['frames_over_50ms'] = sum(row['total_ms'] > 50 for row in rows)
        summary['frames_over_100ms'] = sum(row['total_ms'] > 100 for row in rows)
        args.output.write_text(json.dumps({'summary': summary, 'timeline': rows}, indent=2), encoding='utf-8')
        np.savez_compressed(args.output.with_suffix('.npz'), frames=np.asarray(frames), times=frame_times)
        if frames:
            cv2.imwrite(str(args.output.with_suffix('.png')), frames[-1])
        print(json.dumps(summary, indent=2), flush=True)
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    main()
