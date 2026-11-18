# ######################## analyse the webcam input and retrieve the facelet colors of a single cube face ##############


# pip install opencv_python-3.2.0-cp36-cp36m-win_amd64.whl

import cv2
import sys
import numpy as np
from threading import Event
from time import monotonic, perf_counter
import twophase.vision_params as vision_params
from rubik_robot.vision.face_scanner import scanner
from rubik_robot.vision.solve_guide import guide
from rubik_robot.vision.roi import CameraROI, FACE_MARGIN, FACE_SIZE
from rubik_robot.vision.camera_settings import apply_camera_profile, configure_camera_runtime, CAMERA_WARMUP_SECONDS
from rubik_robot.vision.scan_preview import StableScanPreview

camera_roi = CameraROI()
diagnostic_recorder = None
performance_recorder = None

camera_stop = Event()
camera_error = ""
face_rejection = ""
face_stability_hsv = None
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


def material_color_sample(pixels, minimum_fraction=.55):
    """Measure coherent, strongly colored material while excluding white glare."""
    colored = pixels[(pixels[:, 1] >= vision_params.sat_W+20)
                     & (pixels[:, 2] >= max(35, vision_params.rgb_L))]
    if len(colored) == 0 or len(colored) < len(pixels)*minimum_fraction:
        return None
    selected = colored[colored[:, 1] >= np.percentile(colored[:, 1], 70)]
    angles = selected[:, 0]*np.pi/90
    weights = selected[:, 1]+1
    sine = np.sum(np.sin(angles)*weights)/np.sum(weights)
    cosine = np.sum(np.cos(angles)*weights)/np.sum(weights)
    if np.hypot(sine, cosine) < .9:
        return None
    result = np.median(selected, axis=0)
    result[0] = (np.arctan2(sine, cosine) % (2*np.pi))*90/np.pi
    return result


def blue_glare_material(p):
    """Confirm a blue-tinted center using coherent blue material around its rim."""
    x, y = (int(value) for value in p)
    inner = hsv[max(0, y-18):min(height, y+18), max(0, x-18):min(width, x+18)]
    if inner.size == 0:
        return None
    floor = max(35, vision_params.rgb_L)
    tint = ((inner[:, :, 0] >= vision_params.green_H+1.5)
            & (inner[:, :, 0] < vision_params.blue_H-1.5)
            & (inner[:, :, 1] >= max(12, vision_params.sat_W*.4))
            & (inner[:, :, 2] >= floor))
    if np.mean(tint) < .6:
        return None
    x0, x1 = max(0, x-54), min(width, x+54)
    y0, y1 = max(0, y-54), min(height, y+54)
    yy, xx = np.ogrid[y0-y:y1-y, x0-x:x1-x]
    radius_squared = xx*xx+yy*yy
    ring = (radius_squared >= 40*40) & (radius_squared < 54*54)
    if not np.any(ring):
        return None
    pixels = hsv[y0:y1, x0:x1]
    blue = ((pixels[:, :, 0] >= vision_params.green_H+1.5)
            & (pixels[:, :, 0] < vision_params.blue_H-1.5)
            & (pixels[:, :, 1] >= vision_params.sat_W+20)
            & (pixels[:, :, 2] >= floor))
    if np.mean(blue[ring]) < .2:
        return None
    covered = 0
    for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
        quadrant = ring & (xx*sx >= 0) & (yy*sy >= 0)
        if np.any(quadrant) and np.mean(blue[quadrant]) >= .15:
            covered += 1
    if covered < 2:
        return None
    material = material_color_sample(pixels[ring & blue].astype(np.float32, copy=False))
    if material is None:
        return None
    # A weak bluish patch alone remains uncertain. Its central hue must agree
    # with strong peripheral pixels, rather than a different adjacent color.
    central_hue = np.median(inner[:, :, 0][tint])
    if abs((material[0]-central_hue+90) % 180-90) > 15:
        return None
    return material


def getcolor(p, radius=10, white_value=None):
    """Decide the color of a facelet by its h value (non white) or by s and v (white)."""
    sz = radius
    x, y = (int(value) for value in p)
    rect = hsv[max(0, y - sz):min(height, y + sz),
               max(0, x - sz):min(width, x + sz)]
    if rect.size == 0:
        return np.zeros(3), ""
    pixels = rect.reshape(-1, 3).astype(np.float32, copy=False)
    median = np.median(pixels, axis=0)
    # Hue wraps at 180: averaging red hues 179 and 1 must produce red, not blue.
    angles = pixels[:, 0] * np.pi / 90
    weights = pixels[:, 1] + 1
    median[0] = (np.arctan2(np.sum(np.sin(angles) * weights),
                            np.sum(np.cos(angles) * weights)) % (2 * np.pi)) * 90 / np.pi
    evidence = pixels
    if radius >= 18:
        extended = hsv[max(0, y-30):min(height, y+30), max(0, x-30):min(width, x+30)]
        evidence = extended.reshape(-1, 3).astype(np.float32, copy=False)
        material = material_color_sample(evidence)
        if (material is not None and median[1] > vision_params.sat_W
                and abs((material[0]-median[0]+90) % 180-90) > 15):
            material = None
        if material is None:
            # Stay inside this sticker's cell, but include material around a
            # large reflection that can fill the original 60-pixel patch.
            wider = hsv[max(0, y-42):min(height, y+42), max(0, x-42):min(width, x+42)]
            wider = wider.reshape(-1, 3).astype(np.float32, copy=False)
            material = material_color_sample(wider)
            if (material is not None and median[1] > vision_params.sat_W
                    and abs((material[0]-median[0]+90) % 180-90) > 15):
                material = None
            if material is not None:
                evidence = wider
        if material is not None:
            median = material
        # Circular centers often reflect across their entire middle. Inspect
        # the material near the edge, staying inside this 120-pixel cell.
        x0, x1 = max(0, x-54), min(width, x+54)
        y0, y1 = max(0, y-54), min(height, y+54)
        yy, xx = np.ogrid[y0-y:y1-y, x0-x:x1-x]
        distance_squared = xx*xx + yy*yy
        ring = hsv[y0:y1, x0:x1][(distance_squared >= 40*40) & (distance_squared < 54*54)]
        if len(ring):
            warm_tint = (median[1] > vision_params.sat_W
                         and (median[0] < vision_params.orange_H or median[0] >= vision_params.blue_H))
            edge_material = material_color_sample(ring.astype(np.float32, copy=False),
                                                  minimum_fraction=.25 if warm_tint and median[1] < 80 else .55)
            if edge_material is not None:
                hue_distance = abs((edge_material[0]-median[0]+90) % 180-90)
                # Peripheral fingers or an adjacent sticker must not replace
                # a blue/green material reading with an unrelated warm hue.
                central_orange = vision_params.orange_L <= median[0] < vision_params.orange_H
                edge_orange = vision_params.orange_L <= edge_material[0] < vision_params.orange_H
                warm_conflict = (warm_tint and material is not None and median[1] >= 80
                                 and central_orange != edge_orange)
                if (not warm_conflict and (median[1] <= vision_params.sat_W or hue_distance <= 15)
                        and (material is None or edge_material[1] >= median[1]+12)):
                    median = edge_material
        if (median[1] < vision_params.sat_W+12
                and vision_params.green_H <= median[0] < vision_params.blue_H):
            blue_material = blue_glare_material((x, y))
            if blue_material is not None:
                median = blue_material
    mh, ms, mv = median
    white_value = vision_params.val_W if white_value is None else white_value
    if ms <= vision_params.sat_W:
        if mv < white_value:
            return median, ''
        clipped = (pixels[:, 2] >= 250) & (pixels[:, 1] <= 5)
        if mv >= 250 and np.mean(clipped) > .8:
            # HSV V is the brightest channel. Only near-zero saturation also
            # indicates that all three channels have lost their color detail.
            return median, ''
        # Specular blue can look almost white. A coherent blue tint or a
        # saturated colored minority makes this patch uncertain, not white.
        chromatic = evidence[(evidence[:, 1] >= vision_params.sat_W + 20)
                             & (evidence[:, 2] >= max(35, vision_params.rgb_L))]
        mixed = False
        if len(chromatic) >= len(evidence)*.12:
            chromatic_angles = chromatic[:, 0]*np.pi/90
            coherence = np.hypot(np.mean(np.sin(chromatic_angles)), np.mean(np.cos(chromatic_angles)))
            chromatic_hue = (np.arctan2(np.mean(np.sin(chromatic_angles)),
                                        np.mean(np.cos(chromatic_angles))) % (2*np.pi))*90/np.pi
            mixed = coherence >= .9 and vision_params.yellow_H <= chromatic_hue < vision_params.blue_H
        blue_tint = (vision_params.green_H <= mh < vision_params.blue_H
                     and ms >= max(12, vision_params.sat_W*.4))
        if mixed or blue_tint:
            return median, ''
        return median, 'white'
    elif abs((mh-vision_params.orange_L+90) % 180-90) < .4:
        return median, ''
    elif vision_params.orange_L <= mh < vision_params.orange_H:
        if mv < vision_params.orange_min_V:
            return median, ''
        return median, 'orange'
    elif vision_params.orange_H <= mh < vision_params.yellow_H:
        if mv < vision_params.yellow_min_V:
            return median, ''
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
    # HSV hue is integral. Native range/bitwise operations avoid allocating
    # several full-frame NumPy arrays per color on the Raspberry Pi.
    masks.extend(cv2.bitwise_and(cv2.inRange(hue, int(np.ceil(low)), int(np.ceil(high))-1), color_mask)
                 for low, high in ranges)
    red = cv2.bitwise_or(cv2.inRange(hue, 0, int(np.ceil(vision_params.orange_L))-1),
                        cv2.inRange(hue, int(np.ceil(vision_params.blue_H)), 179))
    masks.append(cv2.bitwise_and(red, color_mask))
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


def locate_calibrated_face(image):
    """Fit six or more observed stickers spanning all three rows and columns."""
    find_squares(image, grid_N)
    points = np.float32(cent)
    grid = np.float32([[col*120+FACE_MARGIN+60, row*120+FACE_MARGIN+60]
                       for row in range(3) for col in range(3)])
    if len(points) < 6:
        return None
    sizes = np.asarray([np.sqrt(abs(cv2.contourArea(box))) for box in sticker_boxes])
    points = points[(sizes > 42) & (sizes < 135)]
    if len(points) < 6:
        return None
    # Translation seeds avoid confusing adjacent rows when the face moves by
    # more than half a cell. The fit still requires evidence in every row/column.
    seeds = (points[:, None]-grid[None]).reshape(-1, 2)
    seeds = seeds[np.linalg.norm(seeds, axis=1) < 100]
    best, best_rank = None, None
    for shift in seeds:
        distances = np.linalg.norm((grid+shift)[:, None]-points[None, :], axis=2)
        matches = distances.argmin(axis=1)
        cells = np.where(distances.min(axis=1) < 35)[0]
        if len(cells) < 6 or len(set(matches[cells])) != len(cells):
            continue
        alignment, inliers = cv2.estimateAffine2D(
            grid[cells], points[matches[cells]], method=cv2.RANSAC, ransacReprojThreshold=8)
        if alignment is None:
            continue
        inliers = inliers.ravel().astype(bool)
        count = int(sum(inliers))
        accepted = cells[inliers]
        if (count < 6 or len(set(accepted//3)) < 3 or len(set(accepted % 3)) < 3):
            continue
        horizontal, vertical = alignment[:, :2].T
        scales = np.linalg.norm([horizontal, vertical], axis=1)
        if (not np.all((scales > .8) & (scales < 1.2))
                or abs(np.dot(horizontal, vertical)/np.prod(scales)) > .22
                or np.linalg.det(alignment[:, :2]) <= 0):
            continue
        projected = cv2.transform(grid[None], alignment)[0]
        displacement = np.max(np.linalg.norm(projected-grid, axis=1))
        if displacement > 105 or (count < 7 and displacement > 60):
            # Six patches can fit a partly covered face spuriously. Large
            # corrections need a seventh independent sticker as evidence.
            continue
        error = np.median(np.linalg.norm(projected[accepted]-points[matches[accepted]], axis=1))
        rank = (count, -error-.005*displacement)
        if best_rank is None or rank > best_rank:
            best, best_rank = (alignment, count), rank
    if best is not None:
        displacement = np.max(np.linalg.norm(cv2.transform(grid[None], best[0])[0]-grid, axis=1))
        if displacement < 3:
            return None  # Do not introduce contour quantization jitter into a calibrated grid.
    return best


def detect_face(frame, roi=None, include_masks=True):
    """Detect only inside optional (x1, y1, x2, y2), returning full-frame geometry."""
    global width, height, hsv, cent, sticker_boxes, face_centers, face_boxes
    global color_mask, white_mask, black_mask
    global face_rejection, face_stability_hsv
    face_rejection = ''
    face_stability_hsv = None
    if roi is None:
        return _detect_face(frame)
    if np.asarray(roi).shape == (4, 2):
        source = np.asarray(roi, dtype=np.float32)
        if (not np.all(np.isfinite(source)) or not cv2.isContourConvex(source)
                or cv2.contourArea(source) < 100):
            raise ValueError('ROI corners must form a convex face')
        target = np.float32([[0, 0], [359, 0], [359, 359], [0, 359]]) + FACE_MARGIN
        transform = cv2.getPerspectiveTransform(source, target)
        inverse = np.linalg.inv(transform)
        size = FACE_SIZE + 2 * FACE_MARGIN
        rectified = cv2.warpPerspective(frame, transform, (size, size))
        placement = locate_calibrated_face(rectified)
        if placement is not None:
            alignment, _ = placement
            correction = np.vstack((cv2.invertAffineTransform(alignment), [0, 0, 1]))
            transform = correction @ transform
            inverse = np.linalg.inv(transform)
            rectified = cv2.warpPerspective(frame, transform, (size, size))
        _prepare_calibrated_grid(rectified, include_masks)
        result = _sample_calibrated_grid(offset=(FACE_MARGIN, FACE_MARGIN))
        if not result[1]:
            original_rejection = face_rejection
            # Recover a small placement error inside the extra border. Only a
            # complete, uniform nine-patch reading can replace a failed reading.
            for dx, dy in ((-16, 0), (16, 0), (0, -16), (0, 16),
                           (-16, -16), (16, -16), (-16, 16), (16, 16)):
                result = _sample_calibrated_grid(offset=(FACE_MARGIN+dx, FACE_MARGIN+dy))
                if result[1]:
                    break
            if not result[1]:
                face_rejection = original_rejection
        def restore(points):
            return cv2.perspectiveTransform(np.asarray(points, dtype=np.float32).reshape(1, -1, 2), inverse)[0]
        cent = list(restore(cent)) if cent else []
        face_centers = list(restore(face_centers)) if face_centers else []
        sticker_boxes = [restore(box) for box in sticker_boxes]
        face_boxes = [restore(box) for box in face_boxes]
        height, width = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        if include_masks:
            color_mask, white_mask, black_mask = [cv2.warpPerspective(mask, inverse, (width, height),
                                                                    flags=cv2.INTER_NEAREST)
                                                for mask in (color_mask, white_mask, black_mask)]
        return result
    x1, y1, x2, y2 = roi
    if not (0 <= x1 < x2 <= frame.shape[1] and 0 <= y1 < y2 <= frame.shape[0]):
        raise ValueError('ROI must lie within the camera frame')
    result = _detect_face(frame[y1:y2, x1:x2])
    offset = np.asarray([x1, y1], dtype=np.float32)
    cent = [point + offset for point in cent]
    sticker_boxes = [box + offset for box in sticker_boxes]
    face_centers = [point + offset for point in face_centers]
    face_boxes = [box + offset for box in face_boxes]
    height, width = frame.shape[:2]
    padding = ((y1, height - y2), (x1, width - x2))
    hsv = np.pad(hsv, padding + ((0, 0),))
    color_mask, white_mask, black_mask = [np.pad(mask, padding)
                                        for mask in (color_mask, white_mask, black_mask)]
    return result


def center_color_confident(sample, color):
    """Reject boundary colors at the center instead of assigning a face identity."""
    hue, saturation, value = sample
    if color == 'white':
        return saturation <= max(0, vision_params.sat_W - 8) and value >= vision_params.val_W + 10
    if saturation < vision_params.sat_W + 12:
        return False
    boundaries = (vision_params.orange_L, vision_params.orange_H, vision_params.yellow_H,
                  vision_params.green_H, vision_params.blue_H)
    return min(abs((hue - boundary + 90) % 180 - 90) for boundary in boundaries) >= 1.5


def _detect_calibrated_grid(frame, offset=(0, 0)):
    """Sample sticker interiors after a user-calibrated face has been rectified."""
    _prepare_calibrated_grid(frame)
    return _sample_calibrated_grid(offset)


def _prepare_calibrated_grid(frame, include_masks=True):
    """Prepare HSV once, shared by every possible placement in this frame."""
    global width, height, hsv, cent, sticker_boxes, face_centers, face_boxes, white_threshold
    global color_mask, white_mask, black_mask
    height, width = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    white_threshold = vision_params.val_W
    color_mask = white_mask = black_mask = None
    if not include_masks:
        return
    saturation, value = hsv[:, :, 1], hsv[:, :, 2]
    white_mask = ((saturation <= vision_params.sat_W) & (value >= white_threshold)).astype(np.uint8)*255
    color_mask = ((saturation > vision_params.sat_W) & (value >= vision_params.rgb_L)).astype(np.uint8)*255
    black_mask = ((color_mask > 0) | (white_mask > 0)).astype(np.uint8)*255


def _sample_calibrated_grid(offset=(0, 0)):
    """Check nine patches without rebuilding full-image HSV or filter masks."""
    global cent, sticker_boxes, face_centers, face_boxes
    global face_rejection, face_stability_hsv
    face_rejection = ''
    face_stability_hsv = None
    cent, sticker_boxes, face_centers, face_boxes = [], [], [], []
    samples = []
    stability_samples = []
    for row in range(3):
        for col in range(3):
            x, y = col*120 + 60 + offset[0], row*120 + 60 + offset[1]
            patch = hsv[y-18:y+18, x-18:x+18]
            stability_sample = np.median(patch.reshape(-1, 3), axis=0)
            angles = patch[:, :, 0].astype(float) * np.pi / 90
            weights = patch[:, :, 1].astype(float) + 1
            stability_sample[0] = (np.arctan2(np.sum(np.sin(angles)*weights),
                                            np.sum(np.cos(angles)*weights)) % (2*np.pi)) * 90 / np.pi
            stability_samples.append(stability_sample)
            sample, color = getcolor((x, y), radius=18)
            location = f'Cell {row+1},{col+1}'
            measurement = 'HSV ' + '/'.join(str(round(float(value))) for value in sample)
            if not color:
                face_rejection = f'{location}: uncertain ({measurement})'
                return [], []
            if row == 1 and col == 1 and not center_color_confident(sample, color):
                face_rejection = f'Center {color}: uncertain ({measurement})'
                return [], []
            bright = patch[:, :, 2] >= max(35, vision_params.rgb_L)
            if np.mean(bright) < .85:
                face_rejection = f'{location}: dark patch / check placement'
                return [], []
            if color == 'white':
                valid = (patch[:, :, 1] <= vision_params.sat_W) & (patch[:, :, 2] >= white_threshold)
            else:
                hue_distance = np.abs((patch[:, :, 0].astype(np.float32) - sample[0] + 90) % 180 - 90)
                valid = (hue_distance <= 15) & (patch[:, :, 1] > vision_params.sat_W) & bright
            if np.mean(valid) < .65:
                if color == 'white':
                    face_rejection = f'{location}: mixed white / glare ({measurement})'
                    return [], []
                interior = hsv[max(0, y-42):y+42, max(0, x-42):x+42].astype(np.float32)
                hue_distance = np.abs((interior[:, :, 0]-sample[0]+90) % 180-90)
                supported = ((hue_distance <= 15) & (interior[:, :, 1] >= vision_params.sat_W+20)
                             & (interior[:, :, 2] >= max(35, vision_params.rgb_L)))
                if (np.mean(supported) < .55
                        and (color != 'blue' or blue_glare_material((x, y)) is None)):
                    face_rejection = f'{location}: mixed {color} ({measurement})'
                    return [], []
            point = np.float32([x, y])
            box = np.float32([[x-45,y-45], [x+45,y-45], [x+45,y+45], [x-45,y+45]])
            cent.append(point)
            sticker_boxes.append(box)
            samples.append((sample, color))
    face_centers, face_boxes = list(cent), list(sticker_boxes)
    face_stability_hsv = np.asarray(stability_samples).reshape(3, 3, 3)
    return ([[samples[row*3+col][0] for col in range(3)] for row in range(3)],
            [[samples[row*3+col][1] for col in range(3)] for row in range(3)])


def _detect_face(frame):
    """Input: BGR frame. Output: HSV/color grids with fitted sticker centers and boxes."""
    global width, height, hsv, face_centers, face_boxes
    height, width = frame.shape[:2]
    smoothed = cv2.GaussianBlur(frame, (3, 3), 0)
    hsv = cv2.cvtColor(smoothed, cv2.COLOR_BGR2HSV)
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
    if any(not color for _, color in samples):
        return [], []
    hsv_grid = [[samples[row * 3 + col][0] for col in range(3)] for row in range(3)]
    color_grid = [[samples[row * 3 + col][1] for col in range(3)] for row in range(3)]
    return hsv_grid, color_grid


def sticker_label_layout(box, label, frame_shape):
    """Fit the entire label inside its sticker, including rotated diamond boxes."""
    polygon = np.asarray(box, dtype=np.float32)
    center = polygon.mean(axis=0)
    size = np.sqrt(abs(cv2.contourArea(polygon)))
    height, width = frame_shape[:2]
    for scale in (.4, .34, .28, .22, .16):
        (text_width, text_height), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, scale, 1)
        for offset in (size*.17, 0, -size*.17):
            x = round(center[0] - text_width/2)
            y = round(center[1] + offset + (text_height-baseline)/2)
            bounds = (x-2, y-text_height-2, x+text_width+2, y+baseline+2)
            left, top, right, bottom = bounds
            corners = ((left, top), (right, top), (right, bottom), (left, bottom))
            if (0 <= left < right < width and 0 <= top < bottom < height
                    and all(cv2.pointPolygonTest(polygon, (float(a), float(b)), True) >= .5
                            for a, b in corners)):
                return (x, y), scale, bounds
    return None


def draw_scan_overlay(frame, colors, state, boxes_override=None):
    """Input: BGR frame, grid and scan state. Output: frame with boxes and labels."""
    boxes = boxes_override if boxes_override is not None else (face_boxes if colors else sticker_boxes)
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
        cv2.circle(frame, (x, y), max(3, min(5, int(size*.06))), (0, 0, 0), 2, cv2.LINE_AA)
        layout = sticker_label_layout(box, color, frame.shape)
        if layout is not None:
            origin, scale, (left, top, right, bottom) = layout
            cv2.rectangle(frame, (left, top), (right, bottom), (20, 20, 20), -1)
            cv2.putText(frame, color, origin, cv2.FONT_HERSHEY_SIMPLEX, scale,
                        (255, 255, 255), 1, cv2.LINE_AA)
    progress = state.get('progress', 0)
    if state['current'] and state['current'][4] in state['faces']:
        progress = 100
    cv2.rectangle(frame, (frame.shape[1] // 2 - 26, 6), (frame.shape[1] // 2 + 26, 29), (35, 35, 35), -1)
    cv2.putText(frame, f"{progress}%", (frame.shape[1] // 2 - 21, 23),
                cv2.FONT_HERSHEY_SIMPLEX, .45, (255, 255, 255), 1, cv2.LINE_AA)
    if not colors and face_rejection:
        # Keep the cause readable instead of truncating it after scanner status.
        scale = min(.43, (frame.shape[1]-16) / max(1, cv2.getTextSize(
            face_rejection, cv2.FONT_HERSHEY_SIMPLEX, 1, 1)[0][0]))
        cv2.rectangle(frame, (0, frame.shape[0]-79), (frame.shape[1], frame.shape[0]-59), (25, 25, 25), -1)
        cv2.putText(frame, face_rejection, (8, frame.shape[0]-64),
                    cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 230, 255), 1, cv2.LINE_AA)
    detection = ('9/9 grid' if colors else 'Checking colors' if boxes_override is not None
                 else f'{len(sticker_boxes)} candidates')
    text = f"{len(state['faces'])}/6 faces | {detection} | {state['message']}"
    cv2.rectangle(frame, (0, frame.shape[0] - 24), (frame.shape[1], frame.shape[0]), (25, 25, 25), -1)
    cv2.putText(frame, text, (8, frame.shape[0] - 8), cv2.FONT_HERSHEY_SIMPLEX, .38, (240, 240, 240), 1, cv2.LINE_AA)
    notice = state.get('capture_notice')
    if notice:
        # OpenCV's built-in font does not support Vietnamese accents.
        heading, instruction = notice
        banner_top = max(32, frame.shape[0] - 146)
        cv2.rectangle(frame, (6, banner_top), (frame.shape[1] - 7, banner_top + 62), (30, 125, 30), -1)
        for offset, text in ((25, heading), (49, instruction)):
            scale = min(.65, (frame.shape[1] - 32) / max(1, cv2.getTextSize(
                text, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0][0]))
            cv2.putText(frame, text, (16, banner_top + offset), cv2.FONT_HERSHEY_SIMPLEX,
                        scale, (255, 255, 255), 2, cv2.LINE_AA)
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


def grab_colors(camera_id=0, backend=None, show_masks=True, warmup_seconds=CAMERA_WARMUP_SECONDS):
    """Input: camera index/backend and mask flag. Output: live preview and scanned faces."""
    global camera_error
    global height, width, color_mask, white_mask, black_mask, face_centers, face_boxes, sticker_boxes
    camera_stop.clear()
    camera_error = ""
    configure_camera_runtime()
    camera_roi.load(camera_id)
    if backend is None and sys.platform == 'linux':
        backend = cv2.CAP_V4L2
    cap = cv2.VideoCapture(camera_id) if backend is None else cv2.VideoCapture(camera_id, backend)
    try:
        if not cap.isOpened():
            camera_error = f"Cannot open camera {camera_id}"
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        settings = apply_camera_profile(cap, camera_id)
        if settings:
            print('Camera profile:', settings)
        warmup_until = monotonic() + warmup_seconds
        windows_ready = False
        preview = StableScanPreview()
        saved_centers = set(scanner.snapshot()['faces'])
        capture_notice = None
        notice_until = 0.0
        while not camera_stop.is_set():
            tick_start = perf_counter()
            ok, frame = cap.read()
            tick_captured = perf_counter()
            if not ok or frame is None:
                camera_error = "Cannot read camera frame"
                break
            if frame.shape[1] > 640:
                scaled_height = round(frame.shape[0] * 640 / frame.shape[1])
                frame = cv2.resize(frame, (640, scaled_height), interpolation=cv2.INTER_AREA)
            roi = camera_roi.selection(frame.shape)
            # A new region must not inherit votes from the old region.
            if windows_ready and roi != previous_roi:
                scanner.set_enabled(scanner.snapshot()['enabled'])
            previous_roi = roi
            remaining = warmup_until - monotonic()
            if remaining > 0:
                # Keep draining frames while exposure/white balance settle.
                # Do not display or save provisional red/orange labels.
                vision_params.face_hsv, vision_params.face_col = [], []
                face_centers, face_boxes, sticker_boxes = [], [], []
                height, width = frame.shape[:2]
                color_mask = white_mask = black_mask = np.zeros((height, width), dtype=np.uint8)
            else:
                vision_params.face_hsv, vision_params.face_col = detect_face(frame, roi, include_masks=show_masks)
            if camera_roi.start is not None or camera_roi.picking is not None:
                vision_params.face_hsv, vision_params.face_col = [], []
                scanner.set_enabled(scanner.snapshot()['enabled'])
                preview.reset()
            preview_colors, preview_boxes = preview.update(frame, vision_params.face_col, face_boxes,
                                                          roi, now=perf_counter())
            scanner.update(vision_params.face_col, hsv_grid=vision_params.face_hsv,
                           displayed_grid=preview_colors, stability_hsv_grid=face_stability_hsv)
            state = scanner.snapshot()
            centers = set(state['faces'])
            added = centers - saved_centers
            if saved_centers - centers:
                capture_notice = None
            if added:
                names = {'yellow': 'VANG', 'green': 'XANH LA', 'red': 'DO',
                         'white': 'TRANG', 'blue': 'XANH DUONG', 'orange': 'CAM'}
                center = sorted(added)[-1]
                capture_notice = (f"DA LUU MAT {names[center]} ({len(centers)}/6)",
                                  'DA DU 6 MAT - DANG KIEM TRA' if len(centers) == 6
                                  else 'XOAY MAT TIEP - KHONG CAN CHO')
                notice_until = tick_start + 2.0
            saved_centers = centers
            if capture_notice and tick_start < notice_until:
                state['capture_notice'] = capture_notice
            if remaining > 0:
                state['message'] = f'Camera settling: {remaining:.1f}s - wait before scanning'
            elif (not vision_params.face_col and face_rejection
                  and camera_roi.start is None and camera_roi.picking is None):
                state['message'] = face_rejection
            if diagnostic_recorder is not None:
                diagnostic_recorder.record(frame, vision_params.face_hsv, vision_params.face_col, roi,
                                           rejection=face_rejection,
                                           state={'faces': list(state['faces']), 'progress': state['progress'],
                                                  'message': state['message']}, displayed=preview_colors)
            tick_detected = perf_counter()
            if performance_recorder is not None:
                performance_recorder.capture(frame, tick_detected)
            annotated = draw_scan_overlay(camera_roi.draw(frame), preview_colors, state, boxes_override=preview_boxes)
            tick_drawn = perf_counter()
            cv2.imshow('Rubik Cube Detection', annotated)
            if not windows_ready:
                cv2.moveWindow('Rubik Cube Detection', 350, 40)
                cv2.setMouseCallback('Rubik Cube Detection', camera_roi.mouse)
                windows_ready = True
            if show_masks:
                cv2.imshow('color_filter mask', cv2.resize(color_mask, (width // 2, height // 2)))
                cv2.imshow('white_filter mask', cv2.resize(white_mask, (width // 2, height // 2)))
                cv2.imshow('black_filter mask', cv2.resize(black_mask, (width // 2, height // 2)))
            key = cv2.waitKey(1) & 0xFF
            if performance_recorder is not None:
                performance_recorder.record(tick_start, tick_captured, tick_detected, tick_drawn,
                                            perf_counter(), vision_params.face_col, state, vision_params.face_hsv,
                                            preview_colors=preview_colors)
            if key == ord('r'):
                camera_roi.region = None
                camera_roi.corners = None
                camera_roi.picking = None
                camera_roi.save()
            if key == ord('p'):
                camera_roi.picking = []
            if key in (ord('x'), ord('q'), 27):
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
        if performance_recorder is not None:
            try:
                performance_recorder.finish()
            except (OSError, cv2.error) as error:
                print(f'Could not save camera performance report: {error}')
        if camera_error:
            print(camera_error)
