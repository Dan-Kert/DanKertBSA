"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
import subprocess
import numpy as np
import cv2 as cv
from threading import Thread, Lock
from time import time
import os
import re

class ADBCapture:
    # threading properties
    stopped = True
    lock = None
    screenshot = None
    # properties
    w = 0
    h = 0
    device_id = None
    fps = 0
    avg_fps = 0

    def __init__(self, device_id=None, resolution=(1080, 1920)):
        """
        Constructor for ADBCapture class
        :param device_id: ADB device ID (e.g., 'emulator-5554' or serial number)
        :param resolution: Expected screen resolution (width, height)
        """
        self.lock = Lock()
        self.device_id = device_id or self.get_default_device()
        self.w, self.h = resolution
        if not self.device_id:
            raise Exception("No ADB device found. Ensure device is connected and ADB is running.")

    def get_default_device(self):
        """
        Get the first available ADB device
        """
        try:
            result = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]
            for line in lines:
                if '\tdevice' in line:
                    return line.split('\t')[0]
        except Exception as e:
            raise Exception(f"Failed to get ADB devices: {e}")
        return None

    def get_screenshot(self):
        """
        Capture screenshot using ADB
        """
        try:
            # Use adb exec-out screencap -p to get PNG directly
            cmd = ['adb', '-s', self.device_id, 'exec-out', 'screencap', '-p']
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode != 0:
                raise Exception(f"ADB screencap failed: {result.stderr.decode()}")

            # Decode PNG to numpy array
            img = cv.imdecode(np.frombuffer(result.stdout, np.uint8), cv.IMREAD_COLOR)
            if img is None:
                raise Exception("Failed to decode screenshot")

            # Keep the screenshot in the device's current orientation.
            # Do NOT rotate here; ADB `input tap` uses the same coordinate space
            # as the screenshot produced by `screencap`.
            self.h, self.w = img.shape[:2]

            return img
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            return None

    def _get_dimension_from_dumpsys_display(self):
        """
        Try to read the current (rotated) display size from `dumpsys display`.
        This is needed because `wm size` often reports the natural orientation (portrait)
        even when the device is currently in landscape.
        """
        cmd = ['adb', '-s', self.device_id, 'shell', 'dumpsys', 'display']
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return None

        text = result.stdout
        # Prefer override info (current rotation), fallback to base info.
        patterns = [
            r"mOverrideDisplayInfo=.*?real (\d+) x (\d+).*?rotation (\d+)",
            r"mBaseDisplayInfo=.*?real (\d+) x (\d+).*?rotation (\d+)",
            r"DisplayDeviceInfo\{.*?,\s*(\d+) x (\d+).*?rotation (\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.DOTALL)
            if match:
                w, h = int(match.group(1)), int(match.group(2))
                return (w, h)
        return None

    def get_dimension(self):
        """
        Get screen dimensions from ADB
        """
        try:
            dumpsys_size = self._get_dimension_from_dumpsys_display()
            if dumpsys_size:
                self.w, self.h = dumpsys_size
                return self.w, self.h

            cmd = ['adb', '-s', self.device_id, 'shell', 'wm', 'size']
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                size_str = result.stdout.strip().split()[-1]  # e.g., "1080x1920"
                w, h = map(int, size_str.split('x'))
                self.w, self.h = w, h
                return w, h
        except Exception as e:
            pass
        # Fallback to default
        return self.w, self.h

    def start(self):
        """
        Start screenshot capture thread
        """
        self.stopped = False
        self.loop_time = time()
        self.count = 0
        t = Thread(target=self.run)
        t.setDaemon(True)
        t.start()

    def stop(self):
        """
        Stop screenshot capture
        """
        self.stopped = True

    def run(self):
        while not self.stopped:
            screenshot = self.get_screenshot()
            if screenshot is not None:
                self.lock.acquire()
                self.screenshot = screenshot
                self.lock.release()

                self.fps = (1 / (time() - self.loop_time))
                self.loop_time = time()
                self.count += 1
                if self.count == 1:
                    self.avg_fps = self.fps
                else:
                    self.avg_fps = (self.avg_fps * self.count + self.fps) / (self.count + 1)
