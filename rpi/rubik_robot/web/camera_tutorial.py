"""Full camera scan/solve tutorial with in-file web and OpenCV compatibility adapters."""

from __future__ import annotations

import sys
import threading
import time as _clock
from datetime import datetime

import cv2 as _opencv
import numpy as np

from rubik_robot.solver.kociemba_solver import solve_cube
from rubik_robot.motion.planner import MotionPlanner
from . import tutorial_moves
from .tutorial_moves import (
    right_cw, right_ccw, left_cw, left_ccw, front_cw, front_ccw,
    back_cw, back_ccw, up_cw, up_ccw, down_cw, down_ccw,
    turn_to_right, turn_to_front,
)

_COLOR_NAMES = {1: 'white', 2: 'yellow', 3: 'blue', 4: 'green', 5: 'red', 6: 'orange'}
_PROMPT_FACES = {'Show Front Face': 'F', 'Show Top Face': 'U', 'Show Down Face': 'D',
                 'Show Right Face': 'R', 'Show Left Face': 'L', 'Show Back Face': 'B'}
_SESSION_LOCK = threading.Lock()
_runtime = None
cv2 = _opencv


class TutorialCancelled(BaseException):
    """Stop a camera loop without terminating the web server."""


class _Mode:
    """Keep the one-row mode shape expected by all scan and move routines."""

    @staticmethod
    def mode(values):
        """Input: Nx9 votes. Output: (1x9 modes, 1x9 counts), smallest code wins ties."""
        values = np.asarray(values)
        modes, counts = [], []
        for column in values.T:
            labels, frequency = np.unique(column, return_counts=True)
            best = int(np.argmax(frequency))
            modes.append(labels[best])
            counts.append(frequency[best])
        return np.asarray([modes]), np.asarray([counts])


stats = _Mode()


class _Timing:
    """Cancellable timing compatible with the tutorial's existing pauses."""

    @staticmethod
    def sleep(seconds):
        """Input: pause seconds. Output: wait, or cancel immediately when stopped."""
        if _runtime.stop_event.wait(seconds):
            raise TutorialCancelled()


time = _Timing()


class _Solver:
    """Reuse the project's Two-Phase engine while retaining standard move notation."""

    @staticmethod
    def solve(state):
        """Input: 54 stickers. Output: standard solution and published UART preview."""
        solution = solve_cube(state)
        actions = MotionPlanner(face_turn_command='TURN').plan(solution)
        with _runtime.lock:
            _runtime.solution = {'state': state, 'moves': solution.split(),
                                 'count': len(solution.split()),
                                 'uart': [action.to_wire() for action in actions]}
            _runtime.phase = 'guiding'
        return solution


kociemba = _Solver()


class _VideoOutput:
    """Accept recording calls without creating an unsolicited video file."""

    def write(self, frame):
        """Input: image. Output: none; annotated frames are published by imshow."""


class _Capture:
    """Own one device and turn cancellation/read errors into controlled exits."""

    def __init__(self, session):
        """Input: configured session. Output: opened device or injected test capture."""
        backends = {'dshow': _opencv.CAP_DSHOW, 'auto': _opencv.CAP_ANY,
                    'msmf': _opencv.CAP_MSMF, 'v4l2': _opencv.CAP_V4L2}
        self.session = session
        self.device = session.video_factory() if session.video_factory else _opencv.VideoCapture(session.index, backends[session.backend])
        if hasattr(self.device, 'set'):
            self.device.set(_opencv.CAP_PROP_FRAME_WIDTH, 640)
            self.device.set(_opencv.CAP_PROP_FRAME_HEIGHT, 480)

    def read(self):
        """Input: none. Output: next BGR frame; raises on stop or device failure."""
        if self.session.stop_event.is_set():
            raise TutorialCancelled()
        ok, frame = self.device.read()
        if not ok or frame is None:
            raise RuntimeError('Camera khong co hinh; kiem tra ID, backend va ung dung dang giu camera.')
        return ok, frame

    def release(self):
        """Input: none. Output: camera handle released."""
        self.device.release()


class _ImageAPI:
    """Local OpenCV facade; never monkey-patches other project camera functions."""

    def __init__(self, session):
        """Input: tutorial session. Output: image API publishing to the web."""
        self.session = session

    def __getattr__(self, name):
        """Input: OpenCV attribute name. Output: unchanged real OpenCV operation."""
        return getattr(_opencv, name)

    def VideoCapture(self, index):
        """Input: legacy device index. Output: session-configured capture."""
        self.session.capture = _Capture(self.session)
        return self.session.capture

    def VideoWriter(self, *args):
        """Input: video settings. Output: in-memory output sink."""
        return _VideoOutput()

    def imshow(self, title, frame):
        """Input: annotated image. Output: latest JPEG for the web, not a desktop window."""
        ok, encoded = _opencv.imencode('.jpg', frame, [_opencv.IMWRITE_JPEG_QUALITY, 85])
        if ok:
            with self.session.lock:
                self.session.jpeg = encoded.tobytes()
                self.session.seq += 1

    def waitKey(self, milliseconds):
        """Input: polling delay. Output: no key, or cancellation when Stop is pressed."""
        if self.session.stop_event.wait(max(milliseconds / 1000, .025)):
            raise TutorialCancelled()
        return -1

    def arrowedLine(self, frame, start, end, *args, **kwargs):
        """Input: original arrow geometry. Output: same arrow with OpenCV integer coordinates."""
        start = tuple(int(round(v)) for v in start)
        end = tuple(int(round(v)) for v in end)
        return _opencv.arrowedLine(frame, start, end, *args, **kwargs)

    def putText(self, frame, text, *args, **kwargs):
        """Input: original scan prompt. Output: annotated frame and web workflow status."""
        with self.session.lock:
            if text in _PROMPT_FACES and self.session.phase == 'scanning':
                self.session.instruction = text
            if text in {'CUBE SOLVED', 'CUBE ALREADY SOLVED'}:
                self.session.phase = 'complete'
                self.session.instruction = text
                if self.session.solution is None and len(self.session.faces) == 6:
                    self.session.publish_solved()
        return _opencv.putText(frame, text, *args, **kwargs)


class CameraTutorial:
    """One complete camera-guidance workflow; all coordination stays in this file."""

    def __init__(self, video_factory=None):
        """Input: optional test capture factory. Output: idle, unopened tutorial."""
        self.video_factory = video_factory
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = None
        self.capture = None
        self.index, self.backend = 1, 'dshow'
        self.phase, self.instruction, self.error = 'idle', '', ''
        self.faces, self.colors, self.solution = {}, [], None
        self.jpeg, self.seq, self.stable = b'', 0, 0
        self.move, self.move_index = '', 0
        self._last_colors = None

    def start(self, index=1, backend='dshow'):
        """Input: camera ID/backend. Output: started complete six-face tutorial thread."""
        if not isinstance(index, int) or not 0 <= index <= 10 or backend not in {'dshow','auto','msmf','v4l2'}:
            raise ValueError('Camera ID/backend khong hop le.')
        if self.thread and self.thread.is_alive():
            raise ValueError('Dung luot huong dan hien tai truoc.')
        if not _SESSION_LOCK.acquire(blocking=False):
            raise ValueError('Da co mot luot huong dan dang chay.')
        self.index, self.backend = index, backend
        self.phase, self.instruction, self.error = 'scanning', 'Show Front Face', ''
        self.faces, self.colors, self.solution = {}, [], None
        self.jpeg, self.seq, self.stable = b'', 0, 0
        self.move, self.move_index, self._last_colors = '', 0, None
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True, name='camera-tutorial')
        try:
            self.thread.start()
        except BaseException:
            _SESSION_LOCK.release()
            raise

    def stop(self):
        """Input: none. Output: cancelled workflow and released camera, or wait error."""
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                raise ValueError('Dang cho camera/solver dung; thu lai sau.')
        if self.phase not in {'complete','error','idle'}:
            self.phase = 'cancelled'

    def snapshot(self):
        """Input: none. Output: serializable progress; no image bytes or native handles."""
        with self.lock:
            return {'phase': self.phase, 'instruction': self.instruction, 'error': self.error,
                    'faces': {f: [_COLOR_NAMES[int(c)] for c in grid] for f, grid in self.faces.items()},
                    'colors': list(self.colors), 'stable': self.stable, 'move': self.move,
                    'index': self.move_index, 'solution': self.solution, 'seq': self.seq,
                    'running': bool(self.thread and self.thread.is_alive()),
                    'camera_index': self.index, 'backend': self.backend}

    def observe_face(self, values):
        """Input: detected numeric face. Output: live colors and consecutive-frame count."""
        signature = tuple(int(v) for v in np.asarray(values).ravel())
        with self.lock:
            self.stable = min(self.stable + 1, 10) if signature == self._last_colors else 1
            self._last_colors = signature
            self.colors = [_COLOR_NAMES[c] for c in signature]

    def record_face(self, prompt, face):
        """Input: scan prompt and voted 1x9 face. Output: saved face in scan orientation."""
        with self.lock:
            self.faces[_PROMPT_FACES[prompt]] = np.asarray(face).reshape(9).tolist()

    def retry_scan(self, error):
        """Input: invalid-state error. Output: restarted scan, preserving original retry flow."""
        with self.lock:
            self.faces, self.solution = {}, None
            self.phase, self.instruction, self.error = 'scanning', 'Show Front Face', error

    def begin_move(self, move, index):
        """Input: full solution token/index. Output: current instruction shown on web."""
        with self.lock:
            self.move, self.move_index = move, index
            self.instruction = 'Next Move: ' + move
            self.phase, self.error = 'guiding', ''

    def move_message(self, *values):
        """Input: move/view message. Output: exact current action prompt on the web."""
        if values and isinstance(values[0], str) and values[0].startswith('Next Move:'):
            with self.lock:
                self.instruction = values[0]

    def finish_move(self, move):
        """Input: verified solution token. Output: completed-token counter incremented once."""
        with self.lock:
            self.move_index += 1

    def publish_solved(self):
        """Input: six already-solved faces. Output: empty solution and canonical cube string."""
        centers = {int(self.faces[f][4]): f for f in 'URFDLB'}
        state = ''.join(centers[int(c)] for f in 'URFDLB' for c in self.faces[f])
        self.solution = {'state': state, 'moves': [], 'count': 0, 'uart': []}

    def _run(self):
        """Input: session configuration. Output: execute all scan/move loops with cleanup."""
        global _runtime, cv2
        _runtime = self
        cv2 = _ImageAPI(self)
        tutorial_moves.configure_runtime(cv2, stats, detect_face, self.move_message)
        try:
            run_tutorial()
            if self.phase != 'complete':
                self.phase = 'cancelled' if self.stop_event.is_set() else 'error'
                if self.phase == 'error':
                    self.error = 'Huong dan ket thuc truoc khi xac nhan cube hoan chinh.'
        except TutorialCancelled:
            if self.phase != 'complete':
                self.phase = 'cancelled'
        except BaseException as exc:
            self.phase, self.error = 'error', str(exc)
        finally:
            if self.capture is not None:
                self.capture.release()
            cv2 = _opencv
            _runtime = None
            _SESSION_LOCK.release()


def concat(up_face,right_face,front_face,down_face,left_face,back_face):
    """Input: six face arrays in URFDLB order. Output: flattened 54-color array."""
    # solution = [up_face,right_face,front_face,down_face,left_face,back_face]
    solution = np.concatenate((up_face, right_face), axis=None)
    solution = np.concatenate((solution, front_face), axis=None)
    solution = np.concatenate((solution, down_face), axis=None)
    solution = np.concatenate((solution, left_face), axis=None)
    solution = np.concatenate((solution, back_face), axis=None)
    # print(solution)
    return solution


def detect_face(bgr_image_input):
    """Input: BGR image. Output: detected nine color codes and sticker boxes."""

    gray = cv2.cvtColor(bgr_image_input,cv2.COLOR_BGR2GRAY)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2,2))
    gray = cv2.morphologyEx(gray, cv2.MORPH_OPEN, kernel)
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

    gray = cv2.adaptiveThreshold(gray,20,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,5,0)
    #cv2.imwrite()
    try:
         _, contours, hierarchy = cv2.findContours(gray,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)
    except:
         contours, hierarchy = cv2.findContours(gray,cv2.RETR_CCOMP,cv2.CHAIN_APPROX_NONE)


    i = 0
    contour_id = 0
    #print(len(contours))
    count = 0
    blob_colors = []
    for contour in contours:
        A1 = cv2.contourArea(contour)
        contour_id = contour_id + 1

        if A1 < 3000 and A1 > 1000:
            perimeter = cv2.arcLength(contour, True)
            epsilon = 0.01 * perimeter
            approx = cv2.approxPolyDP(contour, epsilon, True)
            hull = cv2.convexHull(contour)
            if cv2.norm(((perimeter / 4) * (perimeter / 4)) - A1) < 150:
                #if cv2.ma
                count = count + 1
                x, y, w, h = cv2.boundingRect(contour)
                #cv2.rectangle(bgr_image_input, (x, y), (x + w, y + h), (0, 255, 255), 2)
                #cv2.imshow('cutted contour', bgr_image_input[y:y + h, x:x + w])
                val = (50*y) + (10*x)
                blob_color = np.array(cv2.mean(bgr_image_input[y:y+h,x:x+w])).astype(int)
                cv2.drawContours(bgr_image_input,[contour],0,(255, 255, 0),2)
                cv2.drawContours(bgr_image_input, [approx], 0, (255, 255, 0), 2)
                blob_color = np.append(blob_color, val)
                blob_color = np.append(blob_color, x)
                blob_color = np.append(blob_color, y)
                blob_color = np.append(blob_color, w)
                blob_color = np.append(blob_color, h)
                blob_colors.append(blob_color)
    if len(blob_colors) > 0:
        blob_colors = np.asarray(blob_colors)
        blob_colors = blob_colors[blob_colors[:, 4].argsort()]
    face = np.array([0,0,0,0,0,0,0,0,0])
    if len(blob_colors) == 9:
        #print(blob_colors)
        for i in range(9):
            #print(blob_colors[i])
            if blob_colors[i][0] > 120 and blob_colors[i][1] > 120 and blob_colors[i][2] > 100:
                blob_colors[i][3] = 1
                face[i] = 1
            elif blob_colors[i][0] < 100 and blob_colors[i][1] > 120 and blob_colors[i][2] > 120 and np.abs(blob_colors[i][1]-blob_colors[i][2])<30:
                blob_colors[i][3] = 2
                face[i] = 2
            elif blob_colors[i][0] > blob_colors[i][1] and blob_colors[i][1] > blob_colors[i][2]:
                blob_colors[i][3] = 3
                face[i] = 3
            elif blob_colors[i][1] > blob_colors[i][0] and blob_colors[i][1] > blob_colors[i][2] and np.abs(blob_colors[i][0] - blob_colors[i][2]) < 30:
                blob_colors[i][3] = 4
                face[i] = 4
            elif blob_colors[i][2] > blob_colors[i][0] and blob_colors[i][2] > blob_colors[i][1] and np.abs(blob_colors[i][0] - blob_colors[i][1]) < 30 and blob_colors[i][0] < 80:
                blob_colors[i][3] = 5
                face[i] = 5
            elif blob_colors[i][1] < blob_colors[i][2] and blob_colors[i][0] < blob_colors[i][1] and blob_colors[i][2] > 120:
                blob_colors[i][3] = 6
                face[i] = 6
        #print(face)
        if np.count_nonzero(face) == 9:
            #print(face)
            #print (blob_colors)
            if _runtime is not None:
                _runtime.observe_face(face)
            return face, blob_colors
        else:
            return [0,0], blob_colors
    else:
        return [0,0,0], blob_colors


def find_face(video,videoWriter,uf,rf,ff,df,lf,bf,text = ""):
    """Input: camera, six known faces and prompt. Output: new face after five-frame voting."""
    faces = []
    while True:
        is_ok, bgr_image_input = video.read()

        if not is_ok:
            print("Cannot read video source")
            sys.exit()


        face, blob_colors = detect_face(bgr_image_input)
        bgr_image_input = cv2.putText(bgr_image_input, text, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
        # print(len(face))
        if len(face) == 9:
            faces.append(face)
            if len(faces) == 5:
                face_array = np.array(faces)
                # print('INNNNN')
                # face_array = np.transpose(face_array)
                detected_face = stats.mode(face_array)[0]
                # print(final_face)
                uf = np.asarray(uf)
                ff = np.asarray(ff)
                detected_face = np.asarray(detected_face)
                #print(np.array_equal(detected_face, tf))
                #print(np.array_equal(detected_face, ff))
                faces = []
                if np.array_equal(detected_face, uf) == False and np.array_equal(detected_face, ff) == False and np.array_equal(detected_face, bf) == False and np.array_equal(detected_face, df) == False and np.array_equal(detected_face, lf) == False and np.array_equal(detected_face, rf) == False:
                    _runtime.record_face(text, detected_face)
                    return detected_face
        videoWriter.write(bgr_image_input)
        cv2.imshow("Output Image", bgr_image_input)
        key_pressed = cv2.waitKey(1) & 0xFF
        if key_pressed == 27 or key_pressed == ord('q'):
            break


def run_tutorial():
    """Input: configured tutorial runtime. Output: complete scan and camera-verified solution guidance."""
    up_face = [0, 0]
    front_face = [0, 0]
    left_face = [0, 0]
    right_face = [0, 0]
    down_face = [0, 0]
    back_face = [0, 0]
    video = cv2.VideoCapture(0)
    is_ok, bgr_image_input = video.read()
    broke = 0
    

    if not is_ok:
        print("Cannot read video source")
        sys.exit()

    h1 = bgr_image_input.shape[0]
    w1 = bgr_image_input.shape[1]
    faces = []
    
    try:
        fourcc = cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')
        fname = "OUTPUT5.avi"
        fps = 20.0
        videoWriter = cv2.VideoWriter(fname, fourcc, fps, (w1, h1))
    except:
        print("Error: can't create output video: %s" % fname)
        sys.exit()
    
    while True:
        is_ok, bgr_image_input = video.read()
        if not is_ok:
            break
        while True:
            #print("Show Front Face")
            front_face = find_face(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face, text="Show Front Face")
            mf = front_face[0,4]
            print(front_face)
            print(mf)
            #print("Show Up Face")
            #time.sleep(2)
            up_face = find_face(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face, text="Show Top Face")
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).total_seconds() > 3:
                    break
                else:
                    is_ok, bgr_image_input = video.read()
                    if not is_ok:
                        broke = 1
                        break
                    bgr_image_input = cv2.putText(bgr_image_input, "Show Down Face", (50,50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    videoWriter.write(bgr_image_input)
                    cv2.imshow("Output Image", bgr_image_input)
                    key_pressed = cv2.waitKey(1) & 0xFF
                    if key_pressed == 27 or key_pressed == ord('q'):
                        broke = 1
                        break
            if broke == 1:
                break
            mu = up_face[0, 4]
            print(up_face)
            print(mu)
            #print("Show Down Face")
            #time.sleep(2)
            down_face = find_face(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face, text="Show Down Face")
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).total_seconds() > 3:
                    break
                else:
                    is_ok, bgr_image_input = video.read()
                    if not is_ok:
                        broke = 1
                        break
                    bgr_image_input = cv2.putText(bgr_image_input, "Show Right Face", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    videoWriter.write(bgr_image_input)
                    cv2.imshow("Output Image", bgr_image_input)
                    key_pressed = cv2.waitKey(1) & 0xFF
                    if key_pressed == 27 or key_pressed == ord('q'):
                        broke = 1
                        break
            if broke == 1:
                break
            md = down_face[0, 4]
            print(down_face)
            print(md)
            #print("Show Right Face")
            #time.sleep(2)
            right_face = find_face(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face, text="Show Right Face")
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).total_seconds() > 3:
                    break
                else:
                    is_ok, bgr_image_input = video.read()
                    if not is_ok:
                        broke = 1
                        break
                    bgr_image_input = cv2.putText(bgr_image_input, "Show Left Face", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    videoWriter.write(bgr_image_input)
                    cv2.imshow("Output Image", bgr_image_input)
                    key_pressed = cv2.waitKey(1) & 0xFF
                    if key_pressed == 27 or key_pressed == ord('q'):
                        broke = 1
                        break
            if broke == 1:
                break
            mr = right_face[0, 4]
            print(right_face)
            print(mr)
            #print("Show Left Face")
            #time.sleep(2)
            left_face = find_face(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face, text="Show Left Face")
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).total_seconds() > 3:
                    break
                else:
                    is_ok, bgr_image_input = video.read()
                    if not is_ok:
                        broke = 1
                        break
                    bgr_image_input = cv2.putText(bgr_image_input, "Show Back Face", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    videoWriter.write(bgr_image_input)
                    cv2.imshow("Output Image", bgr_image_input)
                    key_pressed = cv2.waitKey(1) & 0xFF
                    if key_pressed == 27 or key_pressed == ord('q'):
                        broke = 1
                        break
            if broke == 1:
                break
            ml = left_face[0, 4]
            print(left_face)
            print(ml)
            #print("Show Back Face")
            #time.sleep(2)
            back_face = find_face(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face, text="Show Back Face")
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).total_seconds() > 3:
                    break
                else:
                    is_ok, bgr_image_input = video.read()
                    if not is_ok:
                        broke = 1
                        break
                    bgr_image_input = cv2.putText(bgr_image_input, "Show Front Face", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    videoWriter.write(bgr_image_input)
                    cv2.imshow("Output Image", bgr_image_input)
                    key_pressed = cv2.waitKey(1) & 0xFF
                    if key_pressed == 27 or key_pressed == ord('q'):
                        broke = 1
                        break
            if broke == 1:
                break
            mb = back_face[0, 4]
            print(back_face)
            #time.sleep(2)
            print(mb)

            solution = concat(up_face,right_face,front_face,down_face,left_face,back_face)
            #print(solution)
            cube_solved = [mu, mu, mu, mu, mu, mu, mu, mu, mu, mr, mr, mr, mr, mr, mr, mr, mr, mr, mf, mf, mf, mf, mf,
                           mf, mf, mf, mf, md, md, md, md, md, md, md, md, md, ml, ml, ml, ml, ml, ml, ml, ml, ml, mb,
                           mb, mb, mb, mb, mb, mb, mb, mb]
            if (concat(up_face, right_face, front_face, down_face, left_face, back_face) == cube_solved).all():
                # print("CUBE IS SOLVED")
                is_ok, bgr_image_input = video.read()
                bgr_image_input = cv2.putText(bgr_image_input, "CUBE ALREADY SOLVED", (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)
                videoWriter.write(bgr_image_input)
                cv2.imshow("Output Image", bgr_image_input)
                key_pressed = cv2.waitKey(1) & 0xFF
                if key_pressed == 27 or key_pressed == ord('q'):
                    break
                time.sleep(5)
                return

            final_str = ''
            for val in range(len(solution)):
                if solution[val] == mf:
                    final_str = final_str + 'F'
                elif solution[val] == mr:
                    final_str = final_str + 'R'
                elif solution[val] == mb:
                    final_str = final_str + 'B'
                elif solution[val] == ml:
                    final_str = final_str + 'L'
                elif solution[val] == mu:
                    final_str = final_str + 'U'
                elif solution[val] == md:
                    final_str = final_str + 'D'

            print(final_str)
            try:
                solved = kociemba.solve(final_str)
                print(solved)
                break
            except Exception as exc:
                _runtime.retry_scan(str(exc))
                up_face = [0, 0]
                front_face = [0, 0]
                left_face = [0, 0]
                right_face = [0, 0]
                down_face = [0, 0]
                back_face = [0, 0]

        if broke == 1:
            break
        steps = solved.split()
        for move_index, step in enumerate(steps):
            _runtime.begin_move(step, move_index)
            if step == "R":
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_cw(video,videoWriter,up_face,right_face,front_face,down_face,left_face,back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "R'":
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_ccw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "R2":
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "L":
                [up_face, right_face, front_face, down_face, left_face, back_face] = left_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "L'":
                [up_face, right_face, front_face, down_face, left_face, back_face] = left_ccw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "L2":
                [up_face, right_face, front_face, down_face, left_face, back_face] = left_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = left_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "F":
                [up_face, right_face, front_face, down_face, left_face, back_face] = front_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "F'":
                [up_face, right_face, front_face, down_face, left_face, back_face] = front_ccw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "F2":
                [up_face, right_face, front_face, down_face, left_face, back_face] = front_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = front_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "B":
                [up_face, right_face, front_face, down_face, left_face, back_face] = turn_to_right(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = turn_to_front(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "B'":
                #print(up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = turn_to_right(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_ccw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = turn_to_front(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
            elif step == "B2":
                [up_face, right_face, front_face, down_face, left_face, back_face] = turn_to_right(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = right_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = turn_to_front(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "U":
                [up_face, right_face, front_face, down_face, left_face, back_face] = up_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "U'":
                [up_face, right_face, front_face, down_face, left_face, back_face] = up_ccw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "U2":
                [up_face, right_face, front_face, down_face, left_face, back_face] = up_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = up_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "D":
                [up_face, right_face, front_face, down_face, left_face, back_face] = down_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "D'":
                [up_face, right_face, front_face, down_face, left_face, back_face] = down_ccw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))
            elif step == "D2":
                [up_face, right_face, front_face, down_face, left_face, back_face] = down_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                [up_face, right_face, front_face, down_face, left_face, back_face] = down_cw(video, videoWriter, up_face, right_face, front_face, down_face, left_face, back_face)
                #print(concat(up_face, right_face, front_face, down_face, left_face, back_face))

            _runtime.finish_move(step)

        cube_solved = [mu, mu, mu, mu, mu, mu, mu, mu, mu, mr, mr, mr, mr, mr, mr, mr, mr, mr, mf, mf, mf, mf, mf, mf, mf, mf, mf, md, md, md, md, md, md, md, md, md, ml, ml, ml, ml, ml, ml, ml, ml, ml, mb, mb, mb, mb, mb, mb, mb, mb, mb]
        if (concat(up_face, right_face, front_face, down_face, left_face, back_face) == cube_solved).all():
            #print("CUBE IS SOLVED")
            is_ok, bgr_image_input = video.read()
            bgr_image_input = cv2.putText(bgr_image_input, "CUBE SOLVED", (100, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

            videoWriter.write(bgr_image_input)
            cv2.imshow("Output Image", bgr_image_input)
            key_pressed = cv2.waitKey(1) & 0xFF
            if key_pressed == 27 or key_pressed == ord('q'):
                break
            start_time = datetime.now()
            while True:
                if (datetime.now() - start_time).total_seconds() > 5:
                    break
                else:
                    is_ok, bgr_image_input = video.read()
                    if not is_ok:
                        broke = 1
                        break
                    bgr_image_input = cv2.putText(bgr_image_input, "CUBE SOLVED", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
                    videoWriter.write(bgr_image_input)
                    cv2.imshow("Output Image", bgr_image_input)
                    key_pressed = cv2.waitKey(1) & 0xFF
                    if key_pressed == 27 or key_pressed == ord('q'):
                        broke = 1
                        break
            if broke == 1:
                break
            break
        #print(front_face)
        #print(up_face)

        videoWriter.write(bgr_image_input)
        cv2.imshow("Output Image", bgr_image_input)
        # print(count)
        # print(blob_color)
        # print(face)
        key_pressed = cv2.waitKey(1) & 0xFF
        if key_pressed == 27 or key_pressed == ord('q'):
            break
