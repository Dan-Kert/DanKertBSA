"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
import json
from modules.print import bcolors
brawler_stats_dict = json.load(open("brawler_stats.json"))

class Constants:

    brawler_name = "SAMPLE_NAME"

    speed = 2.4 # units: (tiles per second)
    attack_range = 9.33 # units: (tiles)
    heightScaleFactor = 0.158
    
    #! Map's characteristics
    """
    Change this to suit the current map
    If the map have a lots of walls make sharpCorner True otherwise make it False
    If the brawler spawn in the middle of the map make centerOrder False otherwise make it True
    """
    sharpCorner = True
    centerOrder = True
    
    #! ADB Configuration
    """
    ADB device ID. Leave None to auto-detect first device.
    Use 'adb devices' to find your device ID.
    """
    adb_device_id = None  # e.g., "emulator-5554" or "HT123456789"
    
    """
    Expected screen resolution (width, height). Will be auto-detected if possible.
    """
    # Note: on many devices `wm size` returns portrait even when the device is in landscape.
    # The bot auto-detects the *current* (rotated) size via `dumpsys display` and/or screenshots,
    # so this value is only a fallback.
    screen_resolution = (2340, 1080)
    
    """
    Joystick center coordinates for movement simulation.
    Adjust based on your device and Brawl Stars UI.
    """
    # You can set these as:
    # - absolute pixels: (400, 800)
    # - or relative: (0.17, 0.74) meaning (x*w, y*h)
    joystick_center = (0.17, 0.74)  # ~ (400, 800) on 2340x1080
    joystick_radius = 0.12  # fraction of min(w, h) -> ~130px on 1080p height

    # Inactivity warning ("Предупреждение за неактивность! Двигайся!")
    # Enable by saving a cropped screenshot of the warning banner to this path.
    inactivity_template_path = "control/inactivity_warning.png"
    # ROI in relative coords (x1, y1, x2, y2) where the banner appears (top-center by default).
    inactivity_roi = (0.20, 0.02, 0.80, 0.18)
    inactivity_match_threshold = 0.70
    inactivity_cooldown_seconds = 4.0
    # How small the "nudge" is (fraction of joystick_radius)
    inactivity_nudge_radius = 0.25
    inactivity_nudge_duration_ms = 140

    # Combat buttons (absolute pixels or relative 0..1). Defaults for 2340x1080 landscape.
    attack_button = (0.876, 0.74)   # ~ (2050, 800)
    super_button = (0.748, 0.787)   # ~ (1750, 850)
    gadget_button = (0.726, 0.556)  # ~ (1700, 600)

    # How many taps to send per action (helps reliability on some devices).
    attack_taps = 1
    gadget_taps = 1

    #! Change this to True if you have Nvidia graphics card and CUDA installed
    # For Linux ADB mode, PyTorch CPU mode is used by default.
    nvidia_gpu = True

    # Main contants
    """
    Generate a second window with detection annotated
    """
    DEBUG = False

    #! Do not change these
    # Detector constants
    classes = ["Player","Bush","Enemy","Cubebox"]
    """
    Threshold's index correspond with classes's index.
    e.g. First element of classes is player so the first
    element of threshold is threshold for player.
    """
    threshold = [0.37,0.47,0.57,0.65]

    try:
        brawler_stats = brawler_stats_dict[brawler_name.lower().strip()]
        display_str = f"Using {brawler_name.upper()}'s stats if your selected brawler is not {brawler_name.upper()},\nplease manually modify at constants.py."
        standard_hsf = 0.15
        if len(brawler_stats) == 2:
            brawler_stats.append(standard_hsf)
        elif len(brawler_stats) > 3:
            display_str = f"{brawler_name} in brawler_stats.json has more then 3 element, using stats at constants.py"
            brawler_stats = 3*[None]
    except KeyError:
        brawler_stats = 3*[None]
        display_str = f"{brawler_name.upper()}'s stats is not found in the JSON. \nUsing speed, attack_range and heightScaleFactor in constant.py.\nPlease manually modify at constants.py if you have not."
    print("")
    print(bcolors.BOLD + bcolors.OKGREEN + "Creator: https://github.com/dan-kert" + bcolors.ENDC)
    print(bcolors.BOLD + bcolors.OKGREEN + "Repo: https://github.com/dan-kert/DanKertBSA" + bcolors.ENDC)
    print("")
    print(bcolors.WARNING + display_str + bcolors.ENDC)
    speed = brawler_stats[0] or speed # units: (tiles per second)
    attack_range = brawler_stats[1] or attack_range # units: (tiles per second)
    heightScaleFactor = brawler_stats[2] or heightScaleFactor
    print("")
    print(bcolors.OKBLUE + f"speed: {speed} tiles/second \nattack_range: {attack_range} tiles\nHeightScaleFactor: {heightScaleFactor}" + bcolors.ENDC)

    # interface
    if nvidia_gpu is None:
        # load TensorRT interface
        model_file_path = "yolov8_model/yolov8.engine"
        half = False
        imgsz = 640
    elif nvidia_gpu:
        # load pytorch interface
        model_file_path = "yolov8_model/yolov8.pt"
        half = False
        imgsz = (384,640)
    else:
        # load openvino interface
        model_file_path = "yolov8_model/yolov8_openvino_model"
        half = True
        imgsz = (384,640)
    #bot constant
    movement_key = "middle"
    midpoint_offset = 12
    
    float_int_dict = {
        "speed":speed,
        "attack_range":attack_range,
        "heightScaleFactor": heightScaleFactor
    }

    bool_dict = {
        "sharpCorner": sharpCorner,
        "centerOrder": centerOrder,
    }

    for key in float_int_dict:
        assert type(float_int_dict[key]) == float or type(float_int_dict[key]) == int, f"{key.upper()} should be a integer or a float"

    for key in bool_dict:
        assert type(bool_dict[key]) == bool,f"{key.upper()} should be True or False"

if __name__ == "__main__":
    pass
