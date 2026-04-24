"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
import cv2 as cv
from time import sleep
from modules.adb_capture import ADBCapture
from modules.detection import Detection
from constants import Constants

adbcap = ADBCapture(Constants.adb_device_id, Constants.screen_resolution)
# get window dimension
windowSize = adbcap.get_dimension()

# initialize detection class
detector = Detection(windowSize,Constants.model_file_path,Constants.classes,Constants.heightScaleFactor)

adbcap.start()
detector.start()

print(f"ADB Device: {adbcap.device_id}")
print(f"Screen Size: {windowSize}")

while(True):
    screenshot = adbcap.screenshot
    if screenshot is None:
        continue
    detector.update(screenshot)
    detector.annotate_detection_midpoint()
    detector.annotate_fps(adbcap.avg_fps)
    cv.imshow("Detection test",detector.screenshot)

    # press 'q' with the output window focused to exit.
    key = cv.waitKey(1)
    if key == ord('q'):
        adbcap.stop()
        detector.stop()
        cv.destroyAllWindows()
        break
print('Done.')