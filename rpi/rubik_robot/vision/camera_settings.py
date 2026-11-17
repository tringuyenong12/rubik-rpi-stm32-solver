"""Load measured settings for a specific camera without changing other devices."""
import json
from pathlib import Path

import cv2

PROFILE_PATH = Path(__file__).resolve().parents[3] / 'calibration' / 'camera_settings.json'
CAMERA_WARMUP_SECONDS = 2.0


def configure_camera_runtime():
    """Bound OpenCV worker scheduling overhead for small, realtime camera frames."""
    cv2.setNumThreads(2)
VISION_KEYS = ('rgb_L', 'sat_W', 'val_W', 'sigma_C', 'delta_C',
               'orange_L', 'orange_H', 'yellow_H', 'green_H', 'blue_H')
CAPTURE_KEYS = ('AUTO_EXPOSURE', 'EXPOSURE', 'GAIN', 'AUTO_WB', 'WB_TEMPERATURE')


def load_profile(camera_id):
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding='utf-8'))
        profile = data.get(str(camera_id), {})
        return profile if isinstance(profile, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def load_vision_profile(camera_id):
    from twophase import vision_params
    values = load_profile(camera_id).get('vision', {})
    if not isinstance(values, dict):
        return
    for key in VISION_KEYS:
        value = values.get(key)
        if isinstance(value, (int, float)) and 0 <= value <= 255:
            setattr(vision_params, key, value)


def apply_camera_profile(cap, camera_id):
    load_vision_profile(camera_id)
    values = load_profile(camera_id).get('capture', {})
    if not isinstance(values, dict):
        return {}
    result = {}
    for key in CAPTURE_KEYS:
        value = values.get(key)
        if isinstance(value, (int, float)):
            prop = getattr(cv2, 'CAP_PROP_' + key)
            accepted = cap.set(prop, value)
            result[key] = {'requested': value, 'accepted': accepted, 'readback': cap.get(prop)}
    return result
