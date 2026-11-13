"""Validate camera scans and guide verified quarter turns using the TCP solver."""

from collections import deque
from itertools import product
from threading import Lock
from time import monotonic
import socket

import cv2
import numpy as np

from rubik_robot.cube.state import FACE_ORDER, SOLVED_CUBE, validate_cube_string
from rubik_robot.solver.kociemba_solver import normalize_twophase_solution
from rubik_robot.vision.face_scanner import COLORS
from twophase.cubie import basicMoveCube
from twophase.face import FaceCube


TOP_COLORS = dict(zip(COLORS, ('orange', 'yellow', 'yellow', 'red', 'yellow', 'yellow')))
NORMALS = np.asarray([(0, 1, 0), (1, 0, 0), (0, 0, 1), (0, -1, 0), (-1, 0, 0), (0, 0, -1)])
RIGHT = np.asarray([(1, 0, 0), (0, 0, -1), (1, 0, 0), (1, 0, 0), (0, 0, 1), (-1, 0, 0)])
DOWN = np.asarray([(0, 0, 1), (0, -1, 0), (0, -1, 0), (0, 0, -1), (0, -1, 0), (0, -1, 0)])


def rotate_grid(values, turns=1):
    """Input: flat nine stickers and clockwise turns. Output: rotated flat grid."""
    return tuple(np.rot90(np.asarray(values).reshape(3, 3), -turns).reshape(-1).tolist())


def cube_faces(cube):
    """Input: URFDLB definition. Output: color grids keyed by center color."""
    mapping = dict(zip(FACE_ORDER, COLORS))
    return {center: tuple(mapping[value] for value in cube[index*9:index*9+9])
            for index, center in enumerate(COLORS)}


def face_definition(faces):
    """Input: six center-keyed grids. Output: a URFDLB cube definition."""
    mapping = dict(zip(COLORS, FACE_ORDER))
    return ''.join(mapping[value] for center in COLORS for value in faces[center])


def valid_cube(cube):
    """Input: cube definition. Output: whether colors, cubies and parity are physical."""
    try:
        validate_cube_string(cube)
    except ValueError:
        return False
    face = FaceCube()
    return face.from_string(cube) is True and face.to_cubie_cube().verify() is True


def apply_move(cube, move):
    """Input: cube and standard move. Output: cube after that face turn."""
    face = FaceCube()
    if face.from_string(cube) is not True:
        raise ValueError('Invalid cube definition')
    if not move or move[0] not in FACE_ORDER or move[1:] not in ('', "'", '2'):
        raise ValueError(f'Invalid move {move}')
    cubie = face.to_cubie_cube()
    turns = {"'": 3, '2': 2, '': 1}[move[1:]]
    for _ in range(turns):
        cubie.multiply(basicMoveCube[FACE_ORDER.index(move[0])])
    return cubie.to_facelet_cube().to_string()


def hsv_to_lab(samples):
    """Input: OpenCV HSV samples. Output: LAB samples for center-relative matching."""
    samples = np.asarray(samples, dtype=float)
    if samples.size == 0 or samples.size % 3 or not np.all(np.isfinite(samples)):
        raise ValueError('Invalid camera color samples')
    image = np.clip(np.rint(samples.reshape(1, -1, 3)), 0, 255).astype(np.uint8)
    image[:, :, 0] %= 180
    bgr = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(float)


def color_cost(samples, centers):
    """Input: LAB patches/centers. Output: shadow-tolerant color-distance matrix."""
    difference = samples[:, None, :] - centers[None, :, :]
    difference[:, :, 0] *= 0.35
    return np.sum(difference * difference, axis=2)


def minimum_assignment(cost):
    """Input: finite square costs. Output: minimum-cost column assigned to each row."""
    size = len(cost)
    u, v = np.zeros(size+1), np.zeros(size+1)
    matched, previous = np.zeros(size+1, dtype=int), np.zeros(size+1, dtype=int)
    for row in range(1, size+1):
        matched[0], column = row, 0
        best = np.full(size+1, np.inf)
        used = np.zeros(size+1, dtype=bool)
        while True:
            used[column] = True
            current_row = matched[column]
            reduced = cost[current_row-1] - u[current_row] - v[1:]
            improved = (~used[1:]) & (reduced < best[1:])
            best[1:][improved] = reduced[improved]
            previous[1:][improved] = column
            remaining = np.where(~used[1:], best[1:], np.inf)
            next_column = int(np.argmin(remaining)) + 1
            delta = best[next_column]
            u[matched[used]] += delta
            v[used] -= delta
            best[~used] -= delta
            column = next_column
            if matched[column] == 0:
                break
        while column:
            prior = previous[column]
            matched[column] = matched[prior]
            column = prior
    assignment = np.empty(size, dtype=int)
    assignment[matched[1:]-1] = np.arange(size)
    return assignment


def orient_faces(faces):
    """Input: six grids. Output: a unique physically valid orientation or an error."""
    definition = face_definition(faces)
    validate_cube_string(definition)
    if valid_cube(definition):
        return definition
    variants = [tuple(dict.fromkeys(rotate_grid(faces[color], turn) for turn in range(4))) for color in COLORS]
    found = None
    for grids in product(*variants):
        candidate = face_definition(dict(zip(COLORS, grids)))
        if valid_cube(candidate):
            if found is not None and candidate != found:
                raise ValueError('Several face orientations fit. Check top-edge hints and rotate saved faces.')
            found = candidate
    if found is None:
        raise ValueError('Colors or face directions are inconsistent. Check labels and rescan the affected face.')
    return found


def prepare_cube(faces, hsv_faces=None):
    """Input: captured grids/samples. Output: valid cube, canonical faces, centers and note."""
    if set(faces) != set(COLORS):
        raise ValueError('Capture all six center colors first')
    for center, values in faces.items():
        if len(values) != 9 or values[4] != center or any(value not in COLORS for value in values):
            raise ValueError(f'Invalid captured grid for {center}')
    samples = None
    centers = None
    if hsv_faces and set(hsv_faces) == set(COLORS):
        samples = hsv_to_lab([sample for color in COLORS for sample in hsv_faces[color]])
        if samples.shape != (54, 3):
            raise ValueError('Expected 54 camera color samples')
        centers = samples[np.arange(6)*9+4]
    raw = face_definition(faces)
    try:
        definition = orient_faces(faces)
        note = 'Scan validated'
    except ValueError as original_error:
        if samples is None:
            raise original_error
        free = np.asarray([index for index in range(54) if index % 9 != 4])
        slots = np.repeat(np.arange(6), 8)
        costs = color_cost(samples[free], centers)
        assignment = minimum_assignment(costs[:, slots])
        labels = np.repeat(np.arange(6), 9)
        labels[free] = slots[assignment]
        corrected = {color: tuple(COLORS[value] for value in labels[index*9:index*9+9])
                     for index, color in enumerate(COLORS)}
        definition = orient_faces(corrected)
        changed = sum(a != b for a, b in zip(raw, face_definition(corrected)))
        note = f'Center-calibrated colors; corrected {changed} stickers'
    return definition, cube_faces(definition), centers, note


def request_solution(host, port, cube):
    """Input: TCP endpoint/cube. Output: normalized solution verified against the cube."""
    with socket.create_connection((host, port), timeout=30) as connection:
        connection.sendall((cube + '\n').encode('ascii'))
        with connection.makefile('r', encoding='utf-8') as response:
            reply = response.readline(4096).strip()
    if not reply:
        raise ValueError('Server closed the connection without a solution')
    if 'error' in reply.lower() or 'invalid' in reply.lower():
        raise ValueError(reply)
    solution = normalize_twophase_solution(reply)
    result = cube
    for move in solution.split():
        result = apply_move(result, move)
    if result != SOLVED_CUBE:
        raise ValueError(reply or 'Server returned no solution')
    return solution


def turn_paths(view, move, rotation=0):
    """Input: visible face, quarter turn and image rotation. Output: grid-coordinate arrows."""
    view_index, move_index = FACE_ORDER.index(view), FACE_ORDER.index(move[0])
    normal = NORMALS[move_index]
    positions = [(col, row) for row in range(3) for col in range(3)
                 if np.dot(NORMALS[view_index] + (col-1)*RIGHT[view_index] + (row-1)*DOWN[view_index], normal) == 1]
    if len(positions) != 3:
        return []
    middle = np.mean(positions, axis=0)
    point = NORMALS[view_index] + (middle[0]-1)*RIGHT[view_index] + (middle[1]-1)*DOWN[view_index]
    velocity = -np.cross(normal, point)
    if move.endswith("'"):
        velocity = -velocity
    direction = np.asarray([np.dot(velocity, RIGHT[view_index]), np.dot(velocity, DOWN[view_index])], dtype=float)
    direction /= np.linalg.norm(direction)
    path = np.asarray([middle-direction*1.1, middle+direction*1.1])
    return [rotate_points(path, rotation)]


def rotate_points(points, turns):
    """Input: grid points and clockwise image turns. Output: rotated grid points."""
    points = np.asarray(points, dtype=float) - 1
    for _ in range(turns % 4):
        points = np.column_stack((-points[:, 1], points[:, 0]))
    return points + 1


def view_paths(current, target, rotation=0):
    """Input: visible/target faces and image rotation. Output: whole-cube arrow paths."""
    current_index, target_index = FACE_ORDER.index(current), FACE_ORDER.index(target)
    horizontal = np.dot(NORMALS[target_index], RIGHT[current_index])
    vertical = np.dot(NORMALS[target_index], DOWN[current_index])
    if horizontal == 0 and vertical == 0:
        horizontal = 1
    paths = []
    for line in range(3):
        if horizontal:
            path = [(2.1, line), (-.1, line)] if horizontal > 0 else [(-.1, line), (2.1, line)]
        else:
            path = [(line, 2.1), (line, -.1)] if vertical > 0 else [(line, -.1), (line, 2.1)]
        paths.append(rotate_points(path, rotation))
    return paths


def changed_view_rotation(previous, current, rotation):
    """Input: adjacent visible faces/old roll. Output: roll after a quarter whole-cube rotation."""
    if np.dot(NORMALS[previous], NORMALS[current]) != 0:
        return rotation
    angle = rotation * np.pi / 2
    camera_right = np.cos(angle)*RIGHT[previous] - np.sin(angle)*DOWN[previous]
    camera_down = np.sin(angle)*RIGHT[previous] + np.cos(angle)*DOWN[previous]
    axis = np.cross(NORMALS[current], NORMALS[previous])
    camera_right = axis*np.dot(axis, camera_right) - np.cross(axis, camera_right)
    camera_down = axis*np.dot(axis, camera_down) - np.cross(axis, camera_down)
    angle = np.arctan2(np.dot(RIGHT[current], camera_down), np.dot(RIGHT[current], camera_right))
    return round(angle / (np.pi / 2)) % 4


def top_neighbor(view, rotation):
    """Input: visible face/image roll. Output: adjacent center color at the image's top edge."""
    index = FACE_ORDER.index(view)
    angle = rotation * np.pi / 2
    top = -np.sin(angle)*RIGHT[index] - np.cos(angle)*DOWN[index]
    return COLORS[int(np.argmax(NORMALS @ top))]


class SolveGuide:
    """Track a verified cube model and camera-confirmed solver moves."""

    def __init__(self):
        """Input: none. Output: an idle thread-safe guide session."""
        self.lock = Lock()
        self.phase = 'idle'
        self.cube = ''
        self.moves = []
        self.index = 0
        self.centers = None
        self.view = 'F'
        self.rotation = 0
        self.observed = None
        self.observed_rotation = 0
        self.message = ''
        self.hold = deque(maxlen=7)
        self.hold_key = None
        self.hold_started = 0.0
        self.pending_cube = ''
        self.witnesses = []

    def reset(self):
        """Input: none. Output: cancel guidance and clear its model."""
        with self.lock:
            self.phase, self.cube, self.message = 'idle', '', ''
            self.hold.clear()
            self.hold_key = None
            self.centers = None
            self.moves, self.witnesses = [], []
            self.index, self.rotation, self.observed_rotation = 0, 0, 0
            self.observed = None
            self.pending_cube = ''

    def fail(self, message):
        """Input: scan/network error. Output: show a recoverable error with camera still running."""
        with self.lock:
            self.phase, self.message = 'error', str(message)
            self.cube = ''
            self.centers = None
            self.hold.clear()
            self.hold_key = None

    def begin(self, cube, solution, centers=None):
        """Input: validated cube/solution/calibration. Output: start camera-guided quarter turns."""
        if not valid_cube(cube):
            raise ValueError('Guidance requires a physically valid cube')
        if centers is not None and (np.asarray(centers).shape != (6, 3) or not np.all(np.isfinite(centers))):
            raise ValueError('Expected six calibrated LAB centers')
        moves = []
        result = cube
        for token in solution.split():
            result = apply_move(result, token)
            moves.extend([token[0], token[0]] if token.endswith('2') else [token])
        if result != SOLVED_CUBE:
            raise ValueError('Solution does not solve the scanned cube')
        with self.lock:
            self.cube, self.moves, self.index = cube, moves, 0
            self.centers = np.asarray(centers, dtype=float).copy() if centers is not None else None
            self.observed = None
            self.hold.clear()
            self.hold_key = None
            if not moves:
                self.phase, self.message = 'solved', 'CUBE SOLVED!'
            else:
                self._start_move()

    def classify(self, hsv_grid, fallback):
        """Input: live HSV grid/fallback labels. Output: labels calibrated to scanned centers."""
        with self.lock:
            centers = self.centers
            active = self.phase != 'idle'
        if not active or centers is None or np.asarray(hsv_grid).shape != (3, 3, 3):
            return fallback
        labels = np.argmin(color_cost(hsv_to_lab(hsv_grid), centers), axis=1)
        return [[COLORS[value] for value in labels[row:row+3]] for row in (0, 3, 6)]

    def _start_move(self):
        """Input: locked model/index. Output: choose an observable adjacent face for the move."""
        self.pending_cube = apply_move(self.cube, self.moves[self.index])
        before, after = cube_faces(self.cube), cube_faces(self.pending_cube)
        move_index = FACE_ORDER.index(self.moves[self.index][0])
        choices = []
        for index, color in enumerate(COLORS):
            if np.dot(NORMALS[index], NORMALS[move_index]) != 0:
                continue
            if after[color] in [rotate_grid(before[color], turn) for turn in range(4)]:
                continue
            changes = sum(a != b for a, b in zip(before[color], after[color]))
            priority = ('F', 'R', 'L', 'U', 'D', 'B').index(FACE_ORDER[index])
            ambiguity = 4 - len(set(rotate_grid(before[color], turn) for turn in range(4)))
            choices.append((ambiguity, priority, -changes, index))
        if not choices:
            raise ValueError('This move requires another camera view')
        self.view = FACE_ORDER[min(choices)[3]]
        self.phase, self.message = 'align', f'Show {COLORS[FACE_ORDER.index(self.view)]}; keep the top edge aligned'
        self.hold.clear()
        self.witnesses = self._verification_faces()

    def _verification_faces(self):
        """Input: locked before/after states. Output: extra views distinguishing other single turns."""
        expected = cube_faces(self.pending_cube)
        primary = COLORS[FACE_ORDER.index(self.view)]
        alternatives = []
        for face in FACE_ORDER:
            for suffix in ('', "'", '2'):
                candidate = apply_move(self.cube, face+suffix)
                if candidate != self.pending_cube:
                    visible = cube_faces(candidate)
                    if visible[primary] == expected[primary]:
                        alternatives.append(visible)
        views = []
        while alternatives:
            scores = []
            for color in COLORS:
                if color != primary and color not in views:
                    eliminated = sum(candidate[color] not in [rotate_grid(expected[color], turn) for turn in range(4)]
                                     for candidate in alternatives)
                    scores.append((eliminated, color))
            score, color = max(scores)
            if score == 0:
                raise ValueError('Camera observations are ambiguous for this move')
            views.append(color)
            alternatives = [candidate for candidate in alternatives
                            if candidate[color] in [rotate_grid(expected[color], turn) for turn in range(4)]]
        return views

    def _stable(self, key, now):
        """Input: matching observation key/time. Output: stable confirmation after four frames."""
        if not self.hold or self.hold_key != key:
            self.hold.clear()
            self.hold_started = now
            self.hold_key = key
        self.hold.append(True)
        matches = sum(self.hold)
        return matches >= 4 and matches / len(self.hold) >= .8 and now - self.hold_started >= .18

    def observe(self, grid, now=None):
        """Input: live color grid/time. Output: confirm alignment, movement or verification."""
        now = monotonic() if now is None else now
        with self.lock:
            if self.phase in ('idle', 'solved', 'error'):
                return
            if len(grid) != 3 or any(len(row) != 3 for row in grid):
                self.hold.append(False)
                return
            observed = tuple(color for row in grid for color in row)
            if observed[4] not in COLORS:
                self.hold.append(False)
                return
            current = COLORS.index(observed[4])
            if self.observed is not None and self.observed != current:
                self.observed_rotation = changed_view_rotation(self.observed, current, self.observed_rotation)
            self.observed = current
            actual_color = observed[4]
            camera_cube = self.pending_cube if self.phase == 'verify' else self.cube
            actual_face = cube_faces(camera_cube)[actual_color]
            orientations = [turn for turn in range(4) if rotate_grid(actual_face, turn) == observed]
            if orientations:
                if self.observed_rotation not in orientations:
                    self.observed_rotation = orientations[0]
            target = COLORS[FACE_ORDER.index(self.view)]
            if observed[4] != target:
                self.hold.clear()
                self.message = f'Show {target}; rotate the whole cube, keep layers unchanged'
                return
            before = cube_faces(self.cube)[target]
            after = cube_faces(self.pending_cube)[target]
            if self.phase == 'align':
                matches = [turn for turn in range(4) if rotate_grid(before, turn) == observed]
                if not matches:
                    self.hold.append(False)
                    self.message = f'Align {target}, top neighbor {TOP_COLORS[target]}'
                    return
                rotation = self.observed_rotation if self.observed_rotation in matches else matches[0]
                if self._stable(('align', rotation), now):
                    self.rotation, self.phase = rotation, 'turn'
                    self.hold.clear()
                self.message = f'Align {target}, top neighbor {TOP_COLORS[target]}'
                if self.phase == 'turn':
                    self.message = f'Turn {self.moves[self.index]} | keep {top_neighbor(self.view, self.rotation)} at top'
                return
            if self.phase == 'turn':
                if observed == rotate_grid(after, self.rotation):
                    if self._stable(('after', self.index), now):
                        if self.witnesses:
                            self.view = FACE_ORDER[COLORS.index(self.witnesses.pop(0))]
                            self.phase = 'verify'
                            self.message = f'Check turn: show {COLORS[FACE_ORDER.index(self.view)]}'
                            self.hold.clear()
                        else:
                            self._commit()
                else:
                    self.hold.append(False)
                    self.message = f'Turn {self.moves[self.index]} | keep {top_neighbor(self.view, self.rotation)} at top'
                    if observed != rotate_grid(before, self.rotation):
                        self.message = f'Finish {self.moves[self.index]} or undo a wrong turn; keep cube orientation'
                return
            matches = [turn for turn in range(4) if rotate_grid(after, turn) == observed]
            if not matches:
                self.hold.append(False)
                self.message = 'Turn does not match; restore the expected state before continuing'
                return
            rotation = self.observed_rotation if self.observed_rotation in matches else matches[0]
            if self._stable(('verify', self.view, rotation), now):
                self.rotation = rotation
                if self.witnesses:
                    self.view = FACE_ORDER[COLORS.index(self.witnesses.pop(0))]
                    self.hold.clear()
                else:
                    self._commit()

    def _commit(self):
        """Input: confirmed pending move. Output: advance model or display solved state."""
        self.cube = self.pending_cube
        self.index += 1
        self.hold.clear()
        if self.index == len(self.moves):
            self.phase, self.message = 'solved', 'CUBE SOLVED!'
        else:
            self._start_move()

    def snapshot(self):
        """Input: none. Output: immutable model/progress and grid-coordinate arrow paths."""
        with self.lock:
            paths = []
            if self.phase == 'turn':
                paths = turn_paths(self.view, self.moves[self.index], self.rotation)
            elif self.phase in ('align', 'verify') and self.observed is not None:
                current = FACE_ORDER[self.observed]
                if current != self.view:
                    paths = view_paths(current, self.view, self.observed_rotation)
            return {'phase': self.phase, 'cube': self.cube, 'message': self.message,
                    'index': self.index, 'total': len(self.moves), 'view': self.view,
                    'rotation': self.rotation, 'paths': paths}


guide = SolveGuide()
