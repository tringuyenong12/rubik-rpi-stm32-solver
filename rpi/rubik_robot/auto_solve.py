"""Host-side six-pose capture, Two-Phase solving and acknowledged UART execution."""

from dataclasses import dataclass
from contextlib import ExitStack
from threading import Condition, Event, Thread
from time import monotonic

import cv2
import numpy as np

from rubik_robot.cube.state import SOLVED_CUBE
from rubik_robot.motion.planner import MotionPlanner
from rubik_robot.protocol import Command
from rubik_robot.transport.serial_link import SerialLink
from rubik_robot.vision.face_scanner import COLORS, FaceScanner
from rubik_robot.vision.solve_guide import (
    apply_move, color_cost, face_definition, hsv_to_lab, minimum_assignment,
    request_solution, valid_cube,
)


FACE_COLORS = dict(zip('URFDLB', COLORS))


@dataclass(frozen=True)
class ScanPose:
    """Absolute face-up pose, optional capture and clockwise image correction."""

    face: str
    capture: bool = True
    correction: int = 0

    def command(self):
        """Input: pose. Output: existing SCAN_POSE protocol command."""
        return Command('SCAN_POSE', (self.face,))


# Positions refer to the machine at Start, independently of sticker colors.
# The first U is captured in place. Later U commands restore that placement.
SCAN_ROUTE = (ScanPose('U'), ScanPose('F'), ScanPose('D'), ScanPose('B', correction=2),
              ScanPose('U', False), ScanPose('R', correction=1),
              ScanPose('L', correction=3), ScanPose('U', False))


def scan_commands():
    """Input: none. Output: newline-terminated fixed scan route, excluding capture gates."""
    return ''.join(pose.command().to_wire() + '\n' for pose in SCAN_ROUTE[1:])


class AutoSolveCancelled(Exception):
    """No further commands should be issued after the current operation."""


def check_cancel(cancel):
    """Input: cancellation event. Output: raise before the next operation if requested."""
    if cancel.is_set():
        raise AutoSolveCancelled('Stopped. Restore the initial cube placement before restarting.')


def rotate_grid(values, turns):
    """Input: flat nine stickers or nine HSV triples, clockwise turns. Output: flat tuple."""
    values = np.asarray(values)
    shape = (3, 3) + values.shape[1:]
    rotated = np.rot90(values.reshape(shape), -turns, axes=(0, 1)).reshape(values.shape)
    return tuple(tuple(float(v) for v in row) if np.ndim(row) else str(row) for row in rotated)


def machine_faces(cube, position_colors):
    """Input: machine-coordinate state and observed centers. Output: real-color face grids."""
    return {position_colors[face]: tuple(position_colors[value] for value in cube[index*9:index*9+9])
            for index, face in enumerate('URFDLB')}


def prepare_machine_cube(faces, samples, position_colors):
    """Input: real-color captures/poses. Output: validated state in the machine's coordinates."""
    virtual_colors = {actual: FACE_COLORS[face] for face, actual in position_colors.items()}
    virtual_faces = {virtual_colors[center]: tuple(virtual_colors[color] for color in values)
                     for center, values in faces.items()}
    virtual_samples = {virtual_colors[center]: values for center, values in samples.items()}
    cube = face_definition(virtual_faces)
    if valid_cube(cube):
        return cube, machine_faces(cube, position_colors), 'Machine-relative scan validated'
    if set(virtual_samples) != set(COLORS):
        raise ValueError('Colors or machine face directions are inconsistent. Rescan the cube.')
    numeric = hsv_to_lab([sample for center in COLORS for sample in virtual_samples[center]])
    if numeric.shape != (54, 3):
        raise ValueError('Expected 54 camera samples')
    centers = numeric[np.arange(6)*9+4]
    free = np.asarray([index for index in range(54) if index % 9 != 4])
    slots = np.repeat(np.arange(6), 8)
    assignment = minimum_assignment(color_cost(numeric[free], centers)[:, slots])
    labels = np.repeat(np.arange(6), 9)
    labels[free] = slots[assignment]
    corrected = ''.join('URFDLB'[label] for label in labels)
    if not valid_cube(corrected):
        raise ValueError('Calibrated colors or machine face directions are inconsistent. Rescan the cube.')
    changed = sum(before != after for before, after in zip(cube, corrected))
    note = f'Center-calibrated colors; corrected {changed} stickers in machine coordinates'
    return corrected, machine_faces(corrected, position_colors), note


def execute_auto_solve(link, capture, host, port, cancel, emit, solver=request_solution, connect=None):
    """Input: open UART, capture(pose), server, cancellation/event callbacks. Output: solved plan.

    Capture(pose, seen_centers=...) returns colors/HSV. Optional connect opens UART
    after the first face is saved. No command is retried.
    """
    def send(command):
        """Input: one command. Output: await its completion before continuing."""
        check_cancel(cancel)
        emit('command', command.to_wire())
        link.request_completed(command, timeout_s=15)
        check_cancel(cancel)

    faces, samples, position_colors = {}, {}, {}
    emit('route', scan_commands())
    for index, pose in enumerate(SCAN_ROUTE):
        if index:
            emit('status', f'Moving original machine position {pose.face} toward camera...')
            send(pose.command())
        if not pose.capture:
            continue
        emit('status', f'Capturing machine position {pose.face} — any new center color accepted...')
        colors, hsv = capture(pose, seen_centers=tuple(faces))
        check_cancel(cancel)
        if len(colors) != 9 or any(color not in COLORS for color in colors):
            raise ValueError(f'Position {pose.face}: expected nine recognized sticker colors')
        center = colors[4]
        if center in faces:
            raise ValueError(f'Center {center} was already captured. Check the machine pose movement.')
        position_colors[pose.face] = center
        faces[center] = rotate_grid(colors, pose.correction)
        if hsv is not None:
            samples[center] = rotate_grid(hsv, pose.correction)
        emit('orientation', dict(position_colors))
        emit('face', dict(faces))
        emit('status', f'Saved {center} at machine position {pose.face} ({len(faces)}/6).')
        if index == 0:
            check_cancel(cancel)
            emit('status', 'First face saved. Connecting UART and checking PING...')
            if connect is not None:
                connect()
            send(Command('PING'))
    emit('scan_complete', '6/6 faces captured. Initial pose restored. Checking cube...')
    check_cancel(cancel)
    cube, canonical, note = prepare_machine_cube(faces, samples, position_colors)
    emit('face', canonical)
    emit('status', 'Six faces validated. Solving with Two-Phase... ' + note)
    solution = solver(host, port, cube)
    check_cancel(cancel)
    # Independently validate the server plan before any solving movement.
    predicted = cube
    for token in solution.split():
        predicted = apply_move(predicted, token)
    if predicted != SOLVED_CUBE:
        raise ValueError('Server solution does not solve the scanned cube')
    actions = MotionPlanner(face_turn_command='TURN').plan(solution)
    frames = ''.join(action.to_wire() + '\n' for action in actions)
    result = {'cube': cube, 'solution': solution, 'uart': frames, 'position_colors': dict(position_colors)}
    emit('solution', result)
    for index, (token, action) in enumerate(zip(solution.split(), actions), 1):
        emit('status', f'Sending solution {index}/{len(actions)}: {token}')
        send(action.command)
        cube = apply_move(cube, token)
        emit('move', (index, len(actions), machine_faces(cube, position_colors)))
    emit('status', 'AUTO SOLVE COMPLETE — all solution commands confirmed by DONE.')
    return result


class AutoCamera:
    """Continuously drain the camera so each pose receives fresh, settled frames."""

    def __init__(self, options, cancel, preview):
        """Input: launcher camera options, stop event, PNG callback. Output: unopened camera."""
        self.options, self.cancel, self.preview = options, cancel, preview
        self.stop = Event()
        self.condition = Condition()
        self.sequence = 0
        self.latest = None
        self.error = None
        self.thread = None
        self.cap = None

    def __enter__(self):
        """Input: configured device/backend. Output: exclusively owned camera stream."""
        from twophase import vision2

        old = getattr(vision2, 'camera_thread', None)
        deadline = monotonic() + 5
        while old is not None and old.is_alive():
            vision2.camera_stop.set()
            old.join(.08)
            check_cancel(self.cancel)
            if monotonic() >= deadline:
                raise RuntimeError('Previous camera is still closing. Wait and press Start again.')
        check_cancel(self.cancel)
        camera_id, backend, _ = self.options
        self.cap = cv2.VideoCapture(camera_id) if backend is None else cv2.VideoCapture(camera_id, backend)
        if not self.cap.isOpened():
            self.cap.release()
            raise RuntimeError(f'Cannot open camera {camera_id}')
        self.thread = Thread(target=self._read, daemon=True)
        vision2.camera_thread = self.thread
        self.thread.start()
        return self

    def _read(self):
        """Input: active camera. Output: latest frame and capture timestamp under a condition."""
        try:
            while not self.stop.is_set():
                ok, frame = self.cap.read()
                if not ok:
                    raise RuntimeError('Camera stopped producing images')
                with self.condition:
                    self.sequence += 1
                    self.latest = (self.sequence, monotonic(), frame)
                    self.condition.notify_all()
        except Exception as error:
            with self.condition:
                self.error = error
                self.condition.notify_all()

    def __exit__(self, exc_type, exc, tb):
        """Input: session end. Output: stop reader and release the device before navigation."""
        self.stop.set()
        self.thread.join(2)
        self.cap.release()
        self.thread.join(2)
        if self.thread.is_alive():
            raise RuntimeError('Camera reader has not stopped. Close the application before reopening camera.')

    def capture(self, pose, seen_centers=(), timeout_s=12, settle_s=.4):
        """Input: completed robot pose/deadline. Output: voted nine colors and HSV samples."""
        from twophase import vision2

        scanner = FaceScanner(stable_seconds=.25, min_samples=5)
        ready = monotonic() + settle_s
        deadline, sequence, shown = ready + timeout_s, self.sequence, 0.
        diagnostic = 'Looking for all 9 stickers'
        while monotonic() < deadline:
            check_cancel(self.cancel)
            with self.condition:
                self.condition.wait_for(lambda: self.error or self.sequence > sequence, timeout=.1)
                if self.error:
                    raise self.error
                latest = self.latest
            if latest is None or latest[0] <= sequence:
                continue
            sequence, timestamp, frame = latest
            if timestamp < ready:
                continue
            hsv, colors = vision2.detect_face(frame)
            if len(colors) == 3 and all(len(row) == 3 for row in colors) and colors[1][1] in seen_centers:
                diagnostic = f'{colors[1][1]} already captured. Waiting for a new face at position {pose.face}'
                scanner = FaceScanner(stable_seconds=.25, min_samples=5)
                scanner.message = diagnostic
            else:
                scanner.update(colors, hsv_grid=hsv)
                diagnostic = scanner.snapshot()['message']
            state = scanner.snapshot()
            if timestamp - shown >= .1:
                overlay = vision2.draw_scan_overlay(frame.copy(), colors, state)
                # Existing overlay draws in place and may return None.
                image = overlay if overlay is not None else frame.copy()
                image = cv2.resize(image, (480, 360))
                ok, png = cv2.imencode('.png', image)
                if ok:
                    self.preview(png.tobytes())
                shown = timestamp
            if state['faces']:
                center = next(iter(state['faces']))
                return state['faces'][center], state['hsv_faces'].get(center)
        raise TimeoutError(f'Capture {pose.face} failed: {diagnostic}. Check lighting, framing and pose mapping.')


def run_auto_solve(settings, cancel, emit, preview):
    """Input: frozen UI settings and callbacks. Output: close camera/UART after the entire flow."""
    with AutoCamera(settings['camera'], cancel, preview) as camera, ExitStack() as resources:
        link = SerialLink(settings['port'], settings['baud'], timeout_s=15)

        def connect():
            """Input: first face already saved. Output: open UART within the session cleanup scope."""
            resources.enter_context(link)

        return execute_auto_solve(link, camera.capture, settings['host'], settings['server_port'],
                                  cancel, emit, connect=connect)
