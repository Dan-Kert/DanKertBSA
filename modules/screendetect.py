"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """

from threading import Thread, Lock
from time import sleep
from constants import Constants
from modules.adb_input import ADBInput
import os
import cv2 as cv
from time import time

"""
IDLE: When state exit,play and load is finished, state is changed to IDLE so
it doesn't spam the terminal with print.

DETECT: Actively check if player is defeated, play again button and loading in.

EXIT: When brawler is defeated, exit the match and stop the bot.

PLAY: When play again is showed, press it and stop the bot.

LOAD: When loading into the match, start the bot

CONNECTION: When the connection is lost

PLAY: When the main menu of brawl stars

PROCEED: When the match is finished, it will click the proceed button

STARDROP: Whenever there is a star drop in the main menu, it will collect the star drop
"""
class Detectstate:
    IDLE = 0
    DETECT = 1
    EXIT = 2
    PLAY_AGAIN = 3
    LOAD = 4
    CONNECTION = 5
    PLAY = 6
    PROCEED = 7
    STARDROP = 8
    
class Screendetect:
    #RGB value
    defeatedColor = (62,0,0)
    playColor = (224, 186, 8)
    loadColor = (0, 1, 0)
    proceedColor = (35, 115, 255)
    connection_lost_color = (66, 66, 66)
    starDropColor = (222, 72, 227)

    def __init__(self,windowSize,offset, adb_device_id=None) -> None:
        """
        Constructor for the Screendectect class
        """
        self.state = Detectstate.DETECT
        self.lock = Lock()
        self.w = windowSize[0]
        self.h = windowSize[1]
        self.adb_input = ADBInput(adb_device_id)

        # Coordinate (no offsets for ADB)
        self.defeated1 = (round(self.w*0.9656), round(self.h*0.152))
        self.defeated2 = (round(self.w*0.993), round(self.h*0.2046))

        self.starDrop1 = (round(self.w*0.488), round(self.h*0.9303))
        self.starDrop2 = (round(self.w*0.5228), round(self.h*0.9296))

        self.playAgainButton = (round(self.w*0.5903), round(self.h*0.9197))
        self.playButton = (round(self.w*0.9419), round(self.h*0.8949))
        self.exitButton = (round(self.w*0.493), round(self.h*0.9187))
        self.loadButton = (round(self.w*0.8057), round(self.h*0.9675))
        self.proceedButton = (round(self.w*0.8093), round(self.h*0.9165))

        self.connection_lost_cord = (round(self.w*0.4912), round(self.h*0.5525))
        self.reload_button = (round(self.w*0.2824), round(self.h*0.5812))

        # Inactivity warning template (optional)
        self._inactivity_template = None
        self._last_inactivity_nudge = 0.0
        template_path = getattr(Constants, "inactivity_template_path", None)
        if template_path and os.path.exists(template_path):
            img = cv.imread(template_path, cv.IMREAD_GRAYSCALE)
            if img is not None:
                self._inactivity_template = img

    def _resolve_point(self, point):
        if not point or len(point) != 2:
            return (0, 0)
        x, y = point
        try:
            x_f, y_f = float(x), float(y)
        except Exception:
            return (int(x), int(y))
        if 0.0 <= x_f <= 1.0 and 0.0 <= y_f <= 1.0:
            return (round(x_f * self.w), round(y_f * self.h))
        return (round(x_f), round(y_f))

    def _resolve_length(self, value):
        try:
            v = float(value)
        except Exception:
            return 0
        if 0.0 < v <= 1.0:
            return max(1, round(v * min(self.w, self.h)))
        return max(1, round(v))

    def _check_inactivity_warning(self):
        """
        Template-match the inactivity banner text and, if present, return True.
        Requires `Constants.inactivity_template_path` to exist.
        """
        if self._inactivity_template is None or self.screenshot is None:
            return False

        x1r, y1r, x2r, y2r = getattr(Constants, "inactivity_roi", (0.20, 0.02, 0.80, 0.18))
        x1 = max(0, min(self.w - 1, round(x1r * self.w)))
        y1 = max(0, min(self.h - 1, round(y1r * self.h)))
        x2 = max(1, min(self.w, round(x2r * self.w)))
        y2 = max(1, min(self.h, round(y2r * self.h)))
        if x2 <= x1 or y2 <= y1:
            return False

        roi = self.screenshot[y1:y2, x1:x2]
        if roi is None or roi.size == 0:
            return False

        roi_gray = cv.cvtColor(roi, cv.COLOR_BGR2GRAY)
        th, tw = self._inactivity_template.shape[:2]
        if roi_gray.shape[0] < th or roi_gray.shape[1] < tw:
            return False

        res = cv.matchTemplate(roi_gray, self._inactivity_template, cv.TM_CCOEFF_NORMED)
        _, max_val, _, _ = cv.minMaxLoc(res)
        return max_val >= float(getattr(Constants, "inactivity_match_threshold", 0.70))

    def _nudge_joystick(self):
        """
        Do a very small movement to avoid "inactivity" warning.
        """
        jc = self._resolve_point(getattr(Constants, "joystick_center", (0.17, 0.74)))
        jr = self._resolve_length(getattr(Constants, "joystick_radius", 0.12))
        nudge_r = float(getattr(Constants, "inactivity_nudge_radius", 0.25))
        dur_ms = int(getattr(Constants, "inactivity_nudge_duration_ms", 140))

        dx = max(2, round(jr * nudge_r))
        x2 = min(self.w - 1, jc[0] + dx)
        y2 = jc[1]
        self.adb_input.swipe(jc[0], jc[1], x2, y2, duration=max(80, dur_ms))

    def update_bot_stop(self,bot_stopped):
        self.bot_stopped = bot_stopped
    
    def pixel_matches_color(self, screenshot, x, y, color, tolerance=15):
        """
        Check if pixel at (x, y) in screenshot matches color within tolerance
        """
        if screenshot is None or x >= screenshot.shape[1] or y >= screenshot.shape[0]:
            return False
        pixel = screenshot[y, x]  # BGR format
        # Convert to RGB for comparison
        pixel_rgb = (pixel[2], pixel[1], pixel[0])
        return all(abs(pixel_rgb[i] - color[i]) <= tolerance for i in range(3))

    def update_screenshot(self, screenshot):
        """
        Update screenshot for color checking
        """
        self.screenshot = screenshot
    
    def start(self):
        """
        start screendetect
        """
        self.stopped = False
        t = Thread(target=self.run)
        t.setDaemon(True)
        t.start()

    def stop(self):
        """
        stop screendetect
        """
        self.stopped = True

    def run(self):
        while not self.stopped:
            sleep(0.01)
            # Inactivity warning handler (doesn't change state)
            try:
                cooldown = float(getattr(Constants, "inactivity_cooldown_seconds", 4.0))
                if time() - self._last_inactivity_nudge >= cooldown and self._check_inactivity_warning():
                    print("Inactivity warning: nudge movement")
                    self._nudge_joystick()
                    self._last_inactivity_nudge = time()
            except Exception:
                pass

            if self.state == Detectstate.IDLE:
                sleep(3)
                self.state = Detectstate.DETECT
            
            elif self.state == Detectstate.DETECT:
                try:
                    if self.pixel_matches_color(self.screenshot, self.playAgainButton[0], self.playAgainButton[1], self.playColor, tolerance=15):
                        print("Playing again")
                        self.lock.acquire()
                        self.state = Detectstate.PLAY_AGAIN
                        self.lock.release()
                    
                    elif self.pixel_matches_color(self.screenshot, self.loadButton[0], self.loadButton[1], self.loadColor, tolerance=30):
                        print("Loading in")
                        self.lock.acquire()
                        sleep(3)
                        self.state = Detectstate.LOAD
                        self.lock.release()
                    
                    elif (self.pixel_matches_color(self.screenshot, self.defeated1[0], self.defeated1[1], self.defeatedColor, tolerance=15)
                        or self.pixel_matches_color(self.screenshot, self.defeated2[0], self.defeated2[1], self.defeatedColor, tolerance=15)) and not(self.bot_stopped):
                        print("Exiting match")
                        self.lock.acquire()
                        self.state = Detectstate.EXIT
                        self.lock.release()
                    
                    elif (self.pixel_matches_color(self.screenshot, self.starDrop1[0], self.starDrop1[1], self.starDropColor, tolerance=15)
                    or self.pixel_matches_color(self.screenshot, self.starDrop2[0], self.starDrop2[1], self.starDropColor, tolerance=15)):
                        print("Collecting Star Drop")
                        self.lock.acquire()
                        self.state = Detectstate.STARDROP
                        self.lock.release()
                        
                    elif self.pixel_matches_color(self.screenshot, self.playButton[0], self.playButton[1], self.playColor, tolerance=15):
                        print("Play")
                        self.lock.acquire()
                        self.state = Detectstate.PLAY
                        self.lock.release()

                    elif self.pixel_matches_color(self.screenshot, self.proceedButton[0], self.proceedButton[1], self.proceedColor, tolerance=25):
                        print("Proceed")
                        self.lock.acquire()
                        self.state = Detectstate.PROCEED
                        self.lock.release()
                
                except Exception as e:
                    pass
                        
            elif self.state == Detectstate.PLAY_AGAIN:
                # tap the play button
                sleep(0.05)
                self.adb_input.tap(self.playAgainButton[0], self.playAgainButton[1])
                sleep(0.05)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
            
            elif self.state == Detectstate.LOAD:
                sleep(0.1)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
            
            elif self.state == Detectstate.EXIT:
                sleep(5)
                # tap the exit button
                self.adb_input.tap(self.exitButton[0], self.exitButton[1])
                sleep(0.05)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
            
            elif self.state == Detectstate.CONNECTION:
                sleep(20)
                self.adb_input.tap(self.reload_button[0], self.reload_button[1])
                sleep(0.05)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
            
            elif self.state == Detectstate.PLAY:
                # tap the play button
                sleep(0.05)
                self.adb_input.tap(self.playButton[0], self.playButton[1])
                sleep(0.05)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
            
            elif self.state == Detectstate.PROCEED:
                sleep(0.5)
                # double-tap for reliability
                self.adb_input.tap(self.proceedButton[0], self.proceedButton[1])
                sleep(0.1)
                self.adb_input.tap(self.proceedButton[0], self.proceedButton[1])
                sleep(0.5)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
            
            elif self.state == Detectstate.STARDROP:
                # Collect star drop by tapping the bottom-center area a few times.
                tap_x = round(self.w * 0.505)
                tap_y = round(self.h * 0.93)
                for _ in range(8):
                    self.adb_input.tap(tap_x, tap_y)
                    sleep(0.2)
                self.lock.acquire()
                self.state = Detectstate.IDLE
                self.lock.release()
