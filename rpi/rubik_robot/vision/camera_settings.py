"""Load measured settings for a specific camera without changing other devices."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import cv2

PROFILE_PATH = Path(__file__).resolve().parents[3] / 'calibration' / 'camera_settings.json'
CAMERA_WARMUP_SECONDS = 2.0


def configure_camera_runtime():
    """Bound OpenCV worker scheduling overhead for small, realtime camera frames."""
    cv2.setNumThreads(2)
VISION_KEYS = ('rgb_L', 'sat_W', 'val_W', 'sigma_C', 'delta_C',
               'orange_L', 'orange_H', 'orange_min_V', 'yellow_min_V', 'yellow_H', 'green_H', 'blue_H')
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
        value = values.get(key, 0 if key in ('orange_min_V', 'yellow_min_V') else None)
        if isinstance(value, (int, float)) and 0 <= value <= 255:
            setattr(vision_params, key, value)


def apply_camera_profile(cap, camera_id):
    load_vision_profile(camera_id)
    profile = load_profile(camera_id)
    platform_profiles = profile.get('capture_by_platform', {})
    values = (platform_profiles.get(sys.platform, profile.get('capture', {}))
              if isinstance(platform_profiles, dict) else profile.get('capture', {}))
    if not isinstance(values, dict):
        return {}
    result = {}
    for key in CAPTURE_KEYS:
        value = values.get(key)
        if isinstance(value, (int, float)):
            prop = getattr(cv2, 'CAP_PROP_' + key)
            accepted = cap.set(prop, value)
            result[key] = {'requested': value, 'accepted': accepted, 'readback': cap.get(prop)}
    controls = profile.get('v4l2_controls', {})
    if sys.platform == 'linux' and isinstance(controls, dict) and controls and shutil.which('v4l2-ctl'):
        # Manual mode must settle before gain is set; auto mode can overwrite
        # gain when both controls are sent in a single V4L2 batch.
        for key, value in controls.items():
            if not isinstance(key, str) or not key.replace('_', '').isalnum():
                continue
            if not isinstance(value, int):
                continue
            try:
                command = subprocess.run(['v4l2-ctl', '-d', f'/dev/video{int(camera_id)}',
                                          f'--set-ctrl={key}={value}'],
                                         capture_output=True, text=True, timeout=2)
                result['v4l2.'+key] = {'requested': value, 'accepted': command.returncode == 0,
                                        'error': command.stderr.strip()}
            except (OSError, subprocess.TimeoutExpired) as error:
                result['v4l2.'+key] = {'requested': value, 'accepted': False, 'error': str(error)}
    # Read after native controls have settled, for useful logs on unsupported
    # properties and platform-specific exposure units.
    for key in CAPTURE_KEYS:
        if key in result:
            result[key]['readback'] = cap.get(getattr(cv2, 'CAP_PROP_' + key))
    return result
