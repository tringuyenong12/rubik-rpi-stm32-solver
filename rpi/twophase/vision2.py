# ######################## analyse the webcam input and retrieve the facelet colors of a single cube face ##############


# pip install opencv_python-3.2.0-cp36-cp36m-win_amd64.whl

import cv2
import numpy as np
from threading import Event
import twophase.vision_params as vision_params
from rubik_robot.vision.face_scanner import scanner
from rubik_robot.vision.solve_guide import guide

camera_stop = Event()
camera_error = ""
face_centers = []
face_boxes = []
sticker_boxes = []
white_threshold = vision_params.val_W

grid_N = 25  # number of grid-squares in vertical direction

(major, minor, _) = cv2.__version__.split(".")


def drawgrid(img, n):
    """Draw grid onto the webcam output. Only used for debugging purposes."""
    h, w = img.shape[:2]
    sz = h // n
    border = 1 * sz
    for y in range(border, h - border, sz):
        for x in range(border, w - border, sz):
            cv2.rectangle(img, (x, y), (x + sz, y + sz), (0, 0, 0), 1)  # plot small squares in black and white
            cv2.rectangle(img, (x - 1, y - 1), (x + 1 + sz, y + 1 + sz), (255, 255, 255), 1)


def del_duplicates(pts):
    """Delete one of two potential facelet centers stored in pts if they are too close to each other."""
    delta = width / 12  # width is defined global in grabcolors()
    dele = True
    while dele:
        dele = False
        r = range(len(pts))
        for i in r:
            for j in r[i + 1:]:
                if np.linalg.norm(pts[i] - pts[j]) < delta:
                    del pts[j]
                    dele = True
                if dele:
                    break
            if dele:
                break


def medoid(pts):
    """The mediod is the point with the smallest summed distance from the other points.
    This is a candidate for the center facelet."""
    res = np.array([0.0, 0.0])
    smin = 100000
    for i in pts:
        s = 0
        for j in pts:
            s += np.linalg.norm(i - j)
        if s < smin:
            smin = s
            res = i

    return res


def facelets(pts, med):
    """Separate the candidates into edge and corner facelets by their distance from the medoid."""
    ed = []
    co = []
    if med[0] == 0:
        return co, ed  # no edgefacelets detected
    # find shortest distance
    dmin = 10000
    for p in pts:
        d = np.linalg.norm(p - med)
        if 1 < d < dmin:
            dmin = d
    # edgefacelets should be in a distance not more than dmin*1.3
    for p in pts:
        d = np.linalg.norm(p - med)
        if dmin - 1 < d < dmin * 1.3:
            ed.append(p)
    # now find the corner facelets
    for p in pts:
        d = np.linalg.norm(p - med)
        if dmin * 1.3 < d < dmin * 1.7:
            co.append(p)
    return co, ed


def mirr_facelet(co, ed, med):
    """If we have detected a facelet position, the point reflection at the center also gives a facelet position.
     We can use this position in case the other facelet was not detected directly."""
    aef = []
    acf = []
    for p in ed:
        pa = 2 * med - p
        aef.append(pa)
    for p in co:
        pa = 2 * med - p
        acf.append(pa)

    # delete duplicates
    delta = width / 12  # width is defined global in grabcolors()
    for k in range(len(aef) - 1, -1, -1):
        for p in ed:
            if np.linalg.norm(aef[k] - p) < delta:
                del aef[k]
                break

    for k in range(len(acf) - 1, -1, -1):
        for p in co:
            if np.linalg.norm(acf[k] - p) < delta:
                del acf[k]
                break

    return acf, aef


def display_colorname(bgrcap, p):
    """Display the colornames on the webcam picture."""
    p = np.asarray(p, dtype=int)
    _, col = getcolor(p)
    if col in ('blue', 'green', 'red'):
        txtcol = (255, 255, 255)
    else:
        txtcol = (0, 0, 0)
    font = cv2.FONT_HERSHEY_SIMPLEX
    tz = cv2.getTextSize(col, font, 0.4, 1)[0]
    cv2.putText(
        bgrcap, col, tuple(p - (tz[0] // 2, -tz[1] // 2)), font, 0.4, txtcol, 1)


def getcolor(p, radius=10, white_value=None):
    """Decide the color of a facelet by its h value (non white) or by s and v (white)."""
    sz = radius
    x, y = (int(value) for value in p)
    rect = hsv[max(0, y - sz):min(height, y + sz),
               max(0, x - sz):min(width, x + sz)]
    if rect.size == 0:
        return np.zeros(3), ""
    median = rect.reshape(-1, 3).mean(axis=0)
    mh, ms, mv = median
    white_value = vision_params.val_W if white_value is None else white_value
    if ms <= vision_params.sat_W and mv >= white_value:
        return median, 'white'
    elif vision_params.orange_L <= mh < vision_params.orange_H:
        return median, 'orange'
    elif vision_params.orange_H <= mh < vision_params.yellow_H:
        return median, 'yellow'
    elif vision_params.yellow_H <= mh < vision_params.green_H:
        return median, 'green'
    elif vision_params.green_H <= mh < vision_params.blue_H:
        return median, 'blue'
    else:
        return median, 'red'


def getcolors(co, ed, aco, aed, m):
    """Find the colors of the 9 facelets and decide their position on the cube face."""
    global face_centers
    face_centers = []
    centers = [[None for _ in range(3)] for _ in range(3)]
    centers[1][1] = m
    colors = [['' for _ in range(3)] for _ in range(3)]
    s = np.array([0., 0., 0.])
    hsvs = [[s for _ in range(3)] for _ in range(3)]
    cocents = co + aco
    if len(cocents) != 4:
        return [], []
    edcents = ed + aed
    if len(edcents) != 4:
        return [], []
    for i in cocents:
        if i[0] < m[0] and i[1] < m[1]:
            centers[0][0] = i
        elif i[0] > m[0] and i[1] < m[1]:
            centers[0][2] = i
        elif i[0] < m[0] and i[1] > m[1]:
            centers[2][0] = i
        elif i[0] > m[0] and i[1] > m[1]:
            centers[2][2] = i

    for i in edcents:
        if i[1] < m[1] and abs(i[1] - m[1]) > abs(i[0] - m[0]):
            centers[0][1] = i
    for i in edcents:
        if i[0] < m[0] and abs(i[0] - m[0]) > abs(i[1] - m[1]):
            centers[1][0] = i
    for i in edcents:
        if i[0] > m[0] and abs(i[0] - m[0]) > abs(i[1] - m[1]):
            centers[1][2] = i
    for i in edcents:
        if i[1] > m[1] and abs(i[1] - m[1]) > abs(i[0] - m[0]):
            centers[2][1] = i
    if any(point is None for row in centers for point in row):
        return [], []
    for x in range(3):
        for y in range(3):
            hsv_, col = getcolor(centers[x][y])
            colors[x][y] = col
            hsvs[x][y] = hsv_

    face_centers = [point for row in centers for point in row]
    return hsvs, colors


def split_touching_stickers(contour, rectangle):
    """Input: elongated color region. Output: sticker boxes split at narrow connections."""
    x, y, width, height = cv2.boundingRect(contour)
    region = np.zeros((height + 2, width + 2), dtype=np.uint8)
    shifted = contour - np.asarray([[[x - 1, y - 1]]])
    cv2.drawContours(region, [shifted], 0, 255, -1)
    distance = cv2.distanceTransform(region, cv2.DIST_L2, 5)
    cores = (distance > distance.max() * 0.5).astype(np.uint8)
    count, _, stats, centers = cv2.connectedComponentsWithStats(cores)
    if not 2 <= count - 1 <= 3 or np.min(stats[1:, cv2.CC_STAT_AREA]) < 8:
        return []
    sides = list(rectangle[1])
    sides[int(sides[1] > sides[0])] /= count - 1
    if min(sides) / max(sides) < 0.6:
        return []
    result = []
    for center in centers[1:]:
        center = center + (x - 1, y - 1)
        box = cv2.boxPoints((tuple(center), tuple(sides), rectangle[2]))
        result.append((cv2.contourArea(contour) / (count - 1), center, box))
    return result


def find_squares(bgrcap, n, white_value=None):
    """Input: BGR frame and grid scale. Output: sticker centers, boxes and HSV masks."""
    global cent, sticker_boxes, color_mask, white_mask, black_mask, white_threshold
    white_threshold = vision_params.val_W if white_value is None else white_value
    raw_hsv = cv2.cvtColor(bgrcap, cv2.COLOR_BGR2HSV)
    hue, saturation, value = cv2.split(raw_hsv)
    bright = value >= max(35, vision_params.rgb_L)
    hue_float = (hue.astype(np.float32) + 20) % 180 - 20
    mean_hue = cv2.boxFilter(hue_float, -1, (5, 5))
    variance = cv2.boxFilter(hue_float * hue_float, -1, (5, 5)) - mean_hue * mean_hue
    uniform = np.sqrt(np.maximum(variance, 0)) <= vision_params.sigma_C
    uniform &= np.abs(hue_float - mean_hue) <= vision_params.delta_C
    colored = (saturation > vision_params.sat_W) & bright & uniform
    white = (saturation <= vision_params.sat_W) & (value >= white_threshold)
    white_mask = white.astype(np.uint8) * 255
    color_mask = colored.astype(np.uint8) * 255
    black_mask = (bright | white).astype(np.uint8) * 255
    edges = cv2.Canny(cv2.cvtColor(bgrcap, cv2.COLOR_BGR2GRAY), 15, 45)
    boundaries = cv2.dilate(edges, np.ones((2, 2), dtype=np.uint8))
    ranges = ((vision_params.orange_L, vision_params.orange_H),
              (vision_params.orange_H, vision_params.yellow_H),
              (vision_params.yellow_H, vision_params.green_H),
              (vision_params.green_H, vision_params.blue_H))
    masks = [white_mask]
    masks.extend(((hue >= low) & (hue < high) & colored).astype(np.uint8) * 255
                 for low, high in ranges)
    red = ((hue < vision_params.orange_L) | (hue >= vision_params.blue_H)) & colored
    masks.append(red.astype(np.uint8) * 255)
    min_area = max(40, (bgrcap.shape[0] / n) ** 2 * 0.2)
    max_area = bgrcap.shape[0] * bgrcap.shape[1] * 0.16
    candidates = []
    for mask in masks:
        separated = cv2.bitwise_and(mask, cv2.bitwise_not(boundaries))
        separated = cv2.morphologyEx(separated, cv2.MORPH_OPEN, np.ones((2, 2), dtype=np.uint8))
        contours, _ = cv2.findContours(separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if not min_area <= area <= max_area:
                continue
            rectangle = cv2.minAreaRect(contour)
            sides = rectangle[1]
            short, long = min(sides), max(sides)
            if short < 7 or area / (short * long) < 0.55:
                continue
            if short / long < 0.60:
                if long / short < 3.8:
                    candidates.extend(split_touching_stickers(contour, rectangle))
                continue
            candidates.append((area, np.asarray(rectangle[0]), cv2.boxPoints(rectangle)))
    candidates.sort(key=lambda item: item[0], reverse=True)
    # Keep candidate work bounded when the background contains many colored objects.
    candidates = candidates[:80]
    cent = [item[1] for item in candidates]
    sticker_boxes = [item[2] for item in candidates]


def fit_face_grid(points, boxes):
    """Input: candidate centers/boxes. Output: row-major indices of one complete 3x3 face."""
    if len(points) < 9:
        return []
    points = np.asarray(points, dtype=float)
    sizes = np.asarray([np.sqrt(abs(cv2.contourArea(box))) for box in boxes])
    offsets = np.asarray([(col - 1, row - 1) for row in range(3) for col in range(3)])
    best_indices, best_error = [], float('inf')
    for middle in points:
        vectors = points - middle
        lengths = np.linalg.norm(vectors, axis=1)
        neighbors = np.argsort(lengths)[1:9]
        right = [index for index in neighbors if vectors[index, 0] > abs(vectors[index, 1])]
        down = [index for index in neighbors if vectors[index, 1] > abs(vectors[index, 0])]
        for right_index in right:
            for down_index in down:
                a, b = vectors[right_index], vectors[down_index]
                spacing = min(lengths[right_index], lengths[down_index])
                ratio = lengths[right_index] / lengths[down_index]
                cosine = abs(np.dot(a, b)) / (lengths[right_index] * lengths[down_index])
                if spacing < 8 or not 0.6 <= ratio <= 1.65 or cosine > 0.45:
                    continue
                predicted = middle + offsets[:, :1] * a + offsets[:, 1:] * b
                distances = np.linalg.norm(predicted[:, None] - points[None, :], axis=2)
                indices = np.argmin(distances, axis=1)
                errors = distances[np.arange(9), indices] / spacing
                selected_sizes = sizes[indices]
                if len(set(indices)) != 9 or np.max(errors) > 0.32:
                    continue
                if np.min(selected_sizes) < spacing * 0.4 or np.max(selected_sizes) > spacing * 1.25:
                    continue
                error = float(np.mean(errors))
                if error < best_error:
                    best_indices, best_error = indices.tolist(), error
    return best_indices


def detect_face(frame):
    """Input: BGR frame. Output: HSV/color grids with fitted sticker centers and boxes."""
    global width, height, hsv, face_centers, face_boxes
    height, width = frame.shape[:2]
    smoothed = cv2.GaussianBlur(frame, (3, 3), 0)
    hsv = cv2.cvtColor(smoothed, cv2.COLOR_BGR2HSV).astype(float)
    find_squares(smoothed, grid_N)
    indices = fit_face_grid(cent, sticker_boxes)
    if not indices:
        adaptive_white = max(70, min(vision_params.val_W, int(np.percentile(hsv[:, :, 2], 90) * 0.6)))
        if adaptive_white < vision_params.val_W:
            find_squares(smoothed, grid_N, white_value=adaptive_white)
            indices = fit_face_grid(cent, sticker_boxes)
    face_centers = [cent[index] for index in indices]
    face_boxes = [sticker_boxes[index] for index in indices]
    if not indices:
        return [], []
    radii = [max(2, min(10, int(np.sqrt(abs(cv2.contourArea(box))) * 0.2))) for box in face_boxes]
    samples = [getcolor(point, radius, white_threshold) for point, radius in zip(face_centers, radii)]
    hsv_grid = [[samples[row * 3 + col][0] for col in range(3)] for row in range(3)]
    color_grid = [[samples[row * 3 + col][1] for col in range(3)] for row in range(3)]
    return hsv_grid, color_grid


def draw_scan_overlay(frame, colors, state):
    """Input: BGR frame, grid and scan state. Output: frame with boxes and labels."""
    boxes = face_boxes if colors else sticker_boxes
    labels = [color for row in colors for color in row] if colors else []
    for index, box in enumerate(boxes):
        points = np.rint(box).astype(np.int32)
        center = np.mean(box, axis=0)
        size = np.sqrt(abs(cv2.contourArea(box)))
        if labels:
            color = labels[index]
        else:
            _, color = getcolor(center, max(2, min(10, int(size * 0.2))), white_threshold)
        x, y = (int(value) for value in center)
        cv2.polylines(frame, [points], True, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.circle(frame, (x, y), max(3, int(size * 0.16)), (0, 0, 0), 2, cv2.LINE_AA)
        origin = (int(np.min(box[:, 0])), max(12, int(np.min(box[:, 1])) - 3))
        cv2.putText(frame, color, origin, cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(frame, color, origin, cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 255, 0), 1, cv2.LINE_AA)
    progress = state.get('progress', 0)
    if state['current'] and state['current'][4] in state['faces']:
        progress = 100
    cv2.rectangle(frame, (frame.shape[1] // 2 - 26, 6), (frame.shape[1] // 2 + 26, 29), (35, 35, 35), -1)
    cv2.putText(frame, f"{progress}%", (frame.shape[1] // 2 - 21, 23),
                cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1, cv2.LINE_AA)
    detection = '9/9 grid' if colors else f'{len(sticker_boxes)} candidates'
    text = f"{len(state['faces'])}/6 faces | {detection} | {state['message']}"
    cv2.rectangle(frame, (0, frame.shape[0] - 24), (frame.shape[1], frame.shape[0]), (25, 25, 25), -1)
    cv2.putText(frame, text, (8, frame.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, .38, (240, 240, 240), 1, cv2.LINE_AA)
    return frame


def draw_guide_overlay(frame, state):
    """Input: annotated camera frame/guide state. Output: perspective-aligned arrows and progress."""
    if state['phase'] == 'idle':
        return frame
    solved = state['phase'] == 'solved'
    heading = 'CUBE SOLVED!' if solved else f"Step {state['index']+1}/{state['total']}"
    if state['phase'] == 'error':
        heading = 'Check scan / server'
    color = (0, 255, 0) if solved else (255, 255, 255)
    cv2.putText(frame, heading, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .7, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(frame, heading, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, .7, color, 2, cv2.LINE_AA)
    if not solved:
        cv2.putText(frame, state['message'], (12, 51), cv2.FONT_HERSHEY_SIMPLEX, .4, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(frame, state['message'], (12, 51), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1, cv2.LINE_AA)
    if len(face_centers) != 9:
        return frame
    source = np.float32([[0, 0], [2, 0], [2, 2], [0, 2]])
    target = np.float32([face_centers[index] for index in (0, 2, 8, 6)])
    transform = cv2.getPerspectiveTransform(source, target)
    for path in state['paths']:
        pixels = cv2.perspectiveTransform(np.asarray(path, dtype=np.float32).reshape(1, -1, 2), transform)[0]
        start, end = (tuple(np.rint(point).astype(int)) for point in pixels)
        cv2.arrowedLine(frame, start, end, (0, 0, 0), 7, cv2.LINE_AA, tipLength=.2)
        cv2.arrowedLine(frame, start, end, (255, 255, 255), 4, cv2.LINE_AA, tipLength=.2)
    return frame


def grab_colors(camera_id=0, backend=None, show_masks=True):
    """Input: camera index/backend and mask flag. Output: live preview and scanned faces."""
    global camera_error
    camera_stop.clear()
    camera_error = ""
    cap = cv2.VideoCapture(camera_id) if backend is None else cv2.VideoCapture(camera_id, backend)
    try:
        if not cap.isOpened():
            camera_error = f"Cannot open camera {camera_id}"
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        windows_ready = False
        while not camera_stop.is_set():
            ok, frame = cap.read()
            if not ok or frame is None:
                camera_error = "Cannot read camera frame"
                break
            if frame.shape[1] > 640:
                scaled_height = round(frame.shape[0] * 640 / frame.shape[1])
                frame = cv2.resize(frame, (640, scaled_height), interpolation=cv2.INTER_AREA)
            vision_params.face_hsv, vision_params.face_col = detect_face(frame)
            vision_params.face_col = guide.classify(vision_params.face_hsv, vision_params.face_col)
            scanner.update(vision_params.face_col, hsv_grid=vision_params.face_hsv)
            try:
                guide.observe(vision_params.face_col)
            except ValueError as error:
                guide.fail(error)
            state = scanner.snapshot()
            annotated = draw_scan_overlay(frame, vision_params.face_col, state)
            cv2.imshow('Rubik Cube Detection', draw_guide_overlay(annotated, guide.snapshot()))
            if not windows_ready:
                cv2.moveWindow('Rubik Cube Detection', 350, 40)
                windows_ready = True
            if show_masks:
                cv2.imshow('color_filter mask', cv2.resize(color_mask, (width // 2, height // 2)))
                cv2.imshow('white_filter mask', cv2.resize(white_mask, (width // 2, height // 2)))
                cv2.imshow('black_filter mask', cv2.resize(black_mask, (width // 2, height // 2)))
            if cv2.waitKey(5) & 0xFF in (ord('x'), ord('q'), 27):
                break
            if cv2.getWindowProperty('Rubik Cube Detection', cv2.WND_PROP_VISIBLE) < 1:
                break
    except cv2.error as error:
        camera_error = str(error)
    finally:
        cap.release()
        camera_stop.set()
        scanner.update([])
        cv2.destroyAllWindows()
        if camera_error:
            print(camera_error)
