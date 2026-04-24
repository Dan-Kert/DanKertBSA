"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
import cv2 as cv
from time import time,sleep
from modules.adb_capture import ADBCapture
from modules.bot import Brawlbot, BotState
from modules.screendetect import Screendetect, Detectstate
from modules.detection import Detection
from modules.adb_input import ADBInput
from modules.print import bcolors
import os
import json
import subprocess
from pathlib import Path
from constants import Constants, brawler_stats_dict

def stop_all_thread(adbcap,screendetect,bot,detector):
    """
    stop all thread from running
    """
    adbcap.stop()
    detector.stop()
    screendetect.stop()
    bot.stop()
    cv.destroyAllWindows()

def add_two_tuple(tup1,tup2):
    """
    add two tuples
    """
    if not(tup1 is None or tup2 is None):
        return tuple(map(sum, zip(tup1, tup2)))


ROOT_DIR = Path(__file__).resolve().parent
SESSION_STATE_FILE = ROOT_DIR / ".session_state.json"

scrcpy_process = None
scrcpy_enabled = False


def load_session_state():
    try:
        if SESSION_STATE_FILE.exists():
            return json.loads(SESSION_STATE_FILE.read_text())
    except Exception:
        pass
    return {}


def save_session_state(state):
    try:
        SESSION_STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        print(bcolors.WARNING + f"Warning: could not save session state: {e}" + bcolors.ENDC)


def fetch_device_name(device_id):
    try:
        manufacturer = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.manufacturer"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()
        model = subprocess.run(
            ["adb", "-s", device_id, "shell", "getprop", "ro.product.model"],
            capture_output=True, text=True, timeout=3
        ).stdout.strip()
        if manufacturer and model:
            name = f"{manufacturer} {model}".strip()
        else:
            name = model or manufacturer or device_id
        return name
    except Exception:
        return device_id


def get_adb_devices():
    try:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=5)
    except FileNotFoundError:
        return []
    lines = result.stdout.strip().splitlines()[1:]
    devices = []
    for line in lines:
        if not line.strip() or "device" not in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            device_id = parts[0]
            devices.append({"id": device_id, "name": fetch_device_name(device_id)})
    return devices


def apply_brawler_selection(brawler_name):
    Constants.brawler_name = brawler_name
    stats = brawler_stats_dict.get(brawler_name.lower().strip())
    if not stats:
        return
    Constants.speed = float(stats[0])
    Constants.attack_range = float(stats[1])
    if len(stats) > 2:
        Constants.heightScaleFactor = float(stats[2])
    else:
        Constants.heightScaleFactor = 0.15


def choose_adb_device():
    devices = get_adb_devices()
    if not devices:
        print(bcolors.WARNING + "No ADB devices found. Connect a device and try again." + bcolors.ENDC)
        input("Press Enter to continue...")
        return

    if len(devices) == 1:
        selected = devices[0]
        Constants.adb_device_id = selected["id"]
        state = load_session_state()
        state["adb_device_id"] = selected["id"]
        save_session_state(state)
        print(bcolors.OKGREEN + f"ADB device selected: {selected['name']} ({selected['id']})" + bcolors.ENDC)
        input("Press Enter to continue...")
        return

    print("ADB devices:")
    for index, device in enumerate(devices, start=1):
        selected_mark = ""
        if device["id"] == Constants.adb_device_id:
            selected_mark = " [current]"
        print(f"{index}) {device['name']} ({device['id']}){selected_mark}")
    print("Type the device number to select it, or press Enter to return.")
    choice = input("Select device: ").strip().lower()
    if not choice or choice == "exit":
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(devices)):
        print(bcolors.WARNING + "Invalid device choice." + bcolors.ENDC)
        input("Press Enter to continue...")
        return
    selected = devices[int(choice) - 1]
    Constants.adb_device_id = selected["id"]
    state = load_session_state()
    state["adb_device_id"] = selected["id"]
    save_session_state(state)
    print(bcolors.OKGREEN + f"ADB device selected: {selected['name']} ({selected['id']})" + bcolors.ENDC)
    input("Press Enter to continue...")


def choose_brawler():
    brawlers = sorted([name for name in brawler_stats_dict.keys() if name != "//brawler_name"])
    print("Available brawlers:")
    for index, name in enumerate(brawlers, start=1):
        stats = brawler_stats_dict[name]
        hsf = stats[2] if len(stats) > 2 else "default"
        print(f"{index}) {name} - speed {stats[0]} attack_range {stats[1]} heightScaleFactor {hsf}")
    print("Type the brawler number to select it, or press Enter to return.")
    choice = input("Select brawler: ").strip().lower()
    if not choice or choice == "exit":
        return
    if not choice.isdigit() or not (1 <= int(choice) <= len(brawlers)):
        print(bcolors.WARNING + "Invalid brawler choice." + bcolors.ENDC)
        input("Press Enter to continue...")
        return
    selected = brawlers[int(choice) - 1]
    apply_brawler_selection(selected)
    state = load_session_state()
    state["brawler_name"] = selected
    save_session_state(state)
    print(bcolors.OKGREEN + f"Selected brawler: {selected}" + bcolors.ENDC)
    input("Press Enter to continue...")


def get_current_device_label():
    devices = get_adb_devices()
    if not devices:
        return "No ADB device detected"
    if Constants.adb_device_id:
        selected = next((d for d in devices if d["id"] == Constants.adb_device_id), None)
        if selected:
            extra = len(devices) - 1
            more = f" +{extra} other(s)" if extra else ""
            return f"{selected['name']} ({selected['id']}){more}"
    first = devices[0]
    extra = len(devices) - 1
    more = f" +{extra} other(s)" if extra else ""
    return f"{first['name']} ({first['id']}){more}"


def load_previous_session():
    global scrcpy_enabled
    state = load_session_state()
    if state.get("adb_device_id"):
        Constants.adb_device_id = state["adb_device_id"]
    if state.get("brawler_name"):
        apply_brawler_selection(state["brawler_name"])
    if state.get("scrcpy_enabled"):
        scrcpy_enabled = state["scrcpy_enabled"]


def start_scrcpy(device_id):
    global scrcpy_process
    if scrcpy_process is not None:
        return
    try:
        scrcpy_process = subprocess.Popen(
            ["scrcpy", "-s", device_id, "--stay-awake"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        sleep(1)
        if scrcpy_process.poll() is None:
            print(bcolors.OKGREEN + f"Phone mirror (scrcpy) started for device {device_id}" + bcolors.ENDC)
        else:
            scrcpy_process = None
            print(bcolors.WARNING + "Error: scrcpy failed to start. Check if scrcpy is installed and device is authorized." + bcolors.ENDC)
    except FileNotFoundError:
        print(bcolors.WARNING + "Error: scrcpy is not installed. Install it using: apt install scrcpy (Ubuntu/Debian) or brew install scrcpy (macOS)" + bcolors.ENDC)
        scrcpy_process = None
    except Exception as e:
        print(bcolors.WARNING + f"Error starting scrcpy: {e}" + bcolors.ENDC)
        scrcpy_process = None


def stop_scrcpy():
    global scrcpy_process
    if scrcpy_process is not None and scrcpy_process.poll() is None:
        try:
            scrcpy_process.terminate()
            scrcpy_process.wait(timeout=3)
            print(bcolors.OKBLUE + "Phone mirror (scrcpy) stopped" + bcolors.ENDC)
        except Exception:
            scrcpy_process.kill()
        finally:
            scrcpy_process = None


def is_scrcpy_running():
    global scrcpy_process
    if scrcpy_process is None:
        return False
    return scrcpy_process.poll() is None


def get_scrcpy_status():
    status = "✓" if scrcpy_enabled else "✗"
    return status


def main():
    # initialize the ADBCapture class
    adbcap = ADBCapture(Constants.adb_device_id, Constants.screen_resolution)
    # get screen dimension
    screenSize = adbcap.get_dimension()

    # initialize ADB input
    adb_input = ADBInput(adbcap.device_id)

    # initialize detection class
    detector = Detection(screenSize,Constants.model_file_path,Constants.classes,Constants.heightScaleFactor)
    # initialize screendectect class (need to adapt for ADB)
    screendetect = Screendetect(screenSize, (0, 0), adbcap.device_id)  # No offsets for ADB
    # initialize bot class
    bot = Brawlbot(screenSize, (0, 0), Constants.speed, Constants.attack_range, adbcap.device_id)  # No offsets
    
    #start thread
    adbcap.start()
    detector.start()
    screendetect.start()
    
    print(f"ADB Device: {adbcap.device_id}")
    print(f"Screen Size: {screenSize}")

    while True:
        screenshot = adbcap.screenshot
        if screenshot is None:
            continue
        # update screenshot for detector
        detector.update(screenshot)
        screendetect.update_screenshot(screenshot)
        screendetect.update_bot_stop(bot.stopped)
        # check bot state
        if bot.state == BotState.INITIALIZING:
            bot.update_results(detector.results)
        elif bot.state == BotState.SEARCHING:
            bot.update_results(detector.results)
        elif bot.state == BotState.MOVING:
            bot.update_screenshot(screenshot)
            bot.update_results(detector.results)
        elif bot.state == BotState.HIDING:
            bot.update_results(detector.results)
            bot.update_player(detector.player_topleft, detector.player_bottomright)  # No offsets
        elif bot.state == BotState.ATTACKING:
            bot.update_results(detector.results)

        # check screendetect state
        if (screendetect.state ==  Detectstate.EXIT
            or screendetect.state ==  Detectstate.PLAY_AGAIN
            or screendetect.state ==  Detectstate.CONNECTION
            or screendetect.state ==  Detectstate.PLAY
            or screendetect.state == Detectstate.PROCEED):
            bot.stop()
        elif screendetect.state ==  Detectstate.LOAD:
            if bot.stopped:
                #wait for game to load
                sleep(4)
                print("starting bot")
                # reset timestamp and state
                bot.timestamp = time()
                bot.state = BotState.INITIALIZING
                bot.start()

        # display annotated window with FPS
        if Constants.DEBUG:
            detector.annotate_detection_midpoint()
            detector.annotate_border(bot.border_size,bot.tile_w,bot.tile_h)
            detector.annotate_fps(adbcap.avg_fps)
            cv.imshow("Brawl Stars Bot",detector.screenshot)

        # Press q to exit the script
        key = cv.waitKey(1)
        if key == ord('q'):
            #stop all threads
            stop_all_thread(adbcap,screendetect,bot,detector)
            break
    print(bcolors.WARNING +'Exiting bot...' +bcolors.ENDC)
    stop_all_thread(adbcap,screendetect,bot,detector)

def toggle_scrcpy():
    global scrcpy_enabled
    scrcpy_enabled = not scrcpy_enabled
    state = load_session_state()
    state["scrcpy_enabled"] = scrcpy_enabled
    save_session_state(state)
    status = "enabled" if scrcpy_enabled else "disabled"
    print(bcolors.OKGREEN + f"Phone mirror (scrcpy) {status}" + bcolors.ENDC)
    input("Press Enter to continue...")


def show_main_menu():
    load_previous_session()
    while True:
        print("\n--------------------")
        print(bcolors.HEADER + bcolors.BOLD + "Brawl Stars ADB Bot Launcher" + bcolors.ENDC)
        print("--------------------")
        print(f"1) Start Bot")
        print(f"2) ADB Device: {get_current_device_label()}")
        print(f"3) Brawler: {Constants.brawler_name}")
        print(f"4) Phone Mirror (scrcpy) [{get_scrcpy_status()}]")
        print("5) Exit")
        print("Type 'exit' at any time to return to this menu.")
        choice = input("Select option: ").strip().lower()
        print("")
        if choice in {"1", "start", "start bot"}:
            if not Constants.adb_device_id:
                print(bcolors.WARNING + "No ADB device selected, attempting to detect automatically..." + bcolors.ENDC)
                devices = get_adb_devices()
                if len(devices) == 1:
                    Constants.adb_device_id = devices[0]["id"]
                elif len(devices) > 1:
                    print(bcolors.WARNING + "Multiple ADB devices found. Please select a device first." + bcolors.ENDC)
                    continue
                else:
                    print(bcolors.WARNING + "No ADB device found. Please connect a device." + bcolors.ENDC)
                    continue
            if scrcpy_enabled:
                start_scrcpy(Constants.adb_device_id)
            main()
            if is_scrcpy_running():
                stop_scrcpy()
        elif choice in {"2", "adb device", "adb"}:
            choose_adb_device()
        elif choice in {"3", "brawler", "character"}:
            choose_brawler()
        elif choice in {"4", "scrcpy", "mirror", "phone mirror"}:
            toggle_scrcpy()
        elif choice in {"5", "exit", "quit"}:
            print("Exiting...")
            if is_scrcpy_running():
                stop_scrcpy()
            break
        else:
            print(bcolors.WARNING + "Invalid option. Please choose 1, 2, 3, 4 or 5." + bcolors.ENDC)


if __name__ == "__main__":
    print("\n" + bcolors.HEADER + bcolors.BOLD + "Before starting the bot, make sure you have Brawl Stars open on your Android device and selected solo showdown gamemode." + bcolors.ENDC)
    print("\n" + bcolors.UNDERLINE + "IMPORTANT - Ensure ADB is installed and device is connected" + bcolors.ENDC)
    show_main_menu()