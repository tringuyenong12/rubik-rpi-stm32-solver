"""Collect bounded timing records without disk I/O in the live preview loop."""
from collections import deque
import json
from pathlib import Path

import numpy as np
import cv2


class CameraPerformance:
    def __init__(self, path, limit=18000):
        self.path = Path(path)
        self.records = deque(maxlen=limit)
        self.first = None
        self.total = 0
        self.saved_events = []
        self.last_saved = ()
        self.photos = deque(maxlen=180)
        self.next_photo = 0.0

    def capture(self, frame, now):
        if now >= self.next_photo:
            self.photos.append((now, cv2.resize(frame, (320, 240), interpolation=cv2.INTER_AREA)))
            self.next_photo = now + 1

    def record(self, start, captured, detected, drawn, displayed, colors, state, samples=None, preview_colors=None):
        if self.first is None:
            self.first = start
        centers = tuple(state['faces'])
        if centers != self.last_saved:
            self.saved_events.append({'time': displayed-self.first, 'centers': centers, 'faces': dict(state['faces'])})
            self.last_saved = centers
        row = {'time': displayed-self.first, 'capture_ms': (captured-start)*1000,
               'detect_ms': (detected-captured)*1000, 'draw_ms': (drawn-detected)*1000,
               'display_ms': (displayed-drawn)*1000, 'total_ms': (displayed-start)*1000,
               'colors': colors, 'message': state['message']}
        if preview_colors is not None:
            row['display_colors'] = preview_colors
        if samples is not None:
            row['hsv'] = np.asarray(samples).tolist()
        self.records.append(row)
        self.total += 1

    def finish(self):
        if not self.records:
            return
        rows = list(self.records)
        # Ignore only initial device settling when assessing steady preview speed.
        steady = [row for row in rows if row['time'] >= 3]
        if not steady:
            steady = rows
        times = np.diff([row['time'] for row in steady])*1000
        elapsed = steady[-1]['time'] - steady[0]['time']
        summary = {'total_frames': self.total, 'measured_frames': len(steady),
                   'steady_seconds': elapsed, 'fps': (len(steady)-1)/elapsed if elapsed > 0 else 0,
                   'complete_grids': sum(bool(row['colors']) for row in steady),
                   'saved_events': self.saved_events}
        if any('display_colors' in row for row in steady):
            for field, label in (('colors', 'raw'), ('display_colors', 'display')):
                signatures = [tuple(color for line in row.get(field, []) for color in line) for row in steady]
                summary[label+'_label_changes'] = sum(a != b for a, b in zip(signatures, signatures[1:]))
                summary[label+'_visibility_toggles'] = sum(bool(a) != bool(b) for a, b in zip(signatures, signatures[1:]))
        for name in ('capture_ms', 'detect_ms', 'draw_ms', 'display_ms', 'total_ms'):
            values = [row[name] for row in steady]
            summary[name] = {'median': float(np.median(values)), 'p95': float(np.percentile(values, 95)),
                             'max': max(values)}
        if len(times):
            summary['interval_ms'] = {'median': float(np.median(times)), 'p95': float(np.percentile(times, 95)),
                                      'max': float(max(times))}
            summary['intervals_over_50ms'] = int(np.sum(times > 50))
            summary['intervals_over_100ms'] = int(np.sum(times > 100))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        photos = []
        if self.photos:
            directory = self.path.with_suffix('')
            directory.mkdir(parents=True, exist_ok=True)
            for index, (timestamp, frame) in enumerate(self.photos):
                name = f'sample_{index:04d}.png'
                cv2.imwrite(str(directory / name), frame)
                photos.append({'time': timestamp-self.first, 'file': name})
        self.path.write_text(json.dumps({'summary': summary, 'timeline': rows, 'photos': photos}, indent=2), encoding='utf-8')
