"""Camera profiles must use Linux exposure units and ordered UVC controls."""
import unittest
from unittest.mock import Mock, patch

from rubik_robot.vision import camera_settings


class TestCameraSettings(unittest.TestCase):
    def test_linux_profile_overrides_windows_units_and_applies_gain_after_manual_mode(self):
        camera = Mock()
        profile = {
            'capture': {'EXPOSURE': -7},
            'capture_by_platform': {'linux': {'AUTO_EXPOSURE': 1, 'EXPOSURE': 60, 'GAIN': 0}},
            'v4l2_controls': {'auto_exposure': 1, 'exposure_time_absolute': 60, 'gain': 0},
        }
        command = Mock(returncode=0, stderr='')
        with patch.object(camera_settings, 'load_profile', return_value=profile), \
                patch.object(camera_settings.sys, 'platform', 'linux'), \
                patch.object(camera_settings.shutil, 'which', return_value='/usr/bin/v4l2-ctl'), \
                patch.object(camera_settings.subprocess, 'run', return_value=command) as run:
            result = camera_settings.apply_camera_profile(camera, 0)
        camera.set.assert_any_call(camera_settings.cv2.CAP_PROP_EXPOSURE, 60)
        controls = [call.args[0][-1] for call in run.call_args_list]
        self.assertEqual(controls, ['--set-ctrl=auto_exposure=1',
                                    '--set-ctrl=exposure_time_absolute=60', '--set-ctrl=gain=0'])
        self.assertTrue(result['v4l2.gain']['accepted'])

    def test_failed_native_control_is_reported_without_stopping_camera(self):
        with patch.object(camera_settings, 'load_profile', return_value={'v4l2_controls': {'gain': 0}}), \
                patch.object(camera_settings.sys, 'platform', 'linux'), \
                patch.object(camera_settings.shutil, 'which', return_value='/usr/bin/v4l2-ctl'), \
                patch.object(camera_settings.subprocess, 'run', side_effect=OSError('device gone')):
            result = camera_settings.apply_camera_profile(Mock(), 0)
        self.assertFalse(result['v4l2.gain']['accepted'])
        self.assertEqual(result['v4l2.gain']['error'], 'device gone')
