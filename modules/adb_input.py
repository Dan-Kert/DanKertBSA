"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
import subprocess
import time

class ADBInput:
    def __init__(self, device_id=None):
        """
        Constructor for ADBInput class
        :param device_id: ADB device ID
        """
        self.device_id = device_id

    def tap(self, x, y):
        """
        Simulate tap at coordinates (x, y)
        """
        cmd = ['adb', '-s', self.device_id, 'shell', 'input', 'tap', str(x), str(y)]
        subprocess.run(cmd, capture_output=True)

    def swipe(self, x1, y1, x2, y2, duration=500):
        """
        Simulate swipe from (x1, y1) to (x2, y2)
        :param duration: Duration in ms
        """
        cmd = ['adb', '-s', self.device_id, 'shell', 'input', 'swipe', str(x1), str(y1), str(x2), str(y2), str(duration)]
        subprocess.run(cmd, capture_output=True)

    def keyevent(self, keycode):
        """
        Send key event
        :param keycode: Android keycode (e.g., 4 for BACK, 82 for MENU)
        """
        cmd = ['adb', '-s', self.device_id, 'shell', 'input', 'keyevent', str(keycode)]
        subprocess.run(cmd, capture_output=True)

    def mouse_down(self, button, x, y):
        """
        Simulate mouse down (for movement, use swipe or tap)
        Note: ADB doesn't have direct mouse support; approximate with tap or swipe
        """
        # For movement, we'll use swipe with short duration
        pass  # Implement if needed

    def mouse_up(self, button):
        """
        Simulate mouse up
        """
        pass  # Implement if needed

    def move_to(self, x, y):
        """
        Move to position (approximate with tap if needed)
        """
        pass  # ADB doesn't support hover; use tap for actions

    def position(self):
        """
        Get current position (not supported in ADB)
        """
        return (0, 0)  # Placeholder

    def press(self, key, presses=1):
        """
        Press key multiple times
        """
        for _ in range(presses):
            self.keyevent(self.key_to_code(key))
            time.sleep(0.1)

    def key_to_code(self, key):
        """
        Convert key name to Android keycode
        """
        key_map = {
            'e': 33,  # KEYCODE_E
            'w': 51,  # KEYCODE_W
            'a': 29,  # KEYCODE_A
            's': 47,  # KEYCODE_S
            'd': 32,  # KEYCODE_D
            'q': 45,  # KEYCODE_Q
            'space': 62,  # KEYCODE_SPACE
            'enter': 66,  # KEYCODE_ENTER
            'back': 4,   # KEYCODE_BACK
            'home': 3,   # KEYCODE_HOME
        }
        return key_map.get(key.lower(), 0)