"""
 * This is the source code of DanKertBSA, a bot for Brawl Stars on Android using ADB.
 * It is licensed under DanKert License.
 * You should have received a copy of the license in this archive (see LICENSE).
 * Author: DanKert, 2026.
 """
import argparse
import os
import subprocess
from datetime import datetime


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _default_device_id():
    result = _run(["adb", "devices"])
    lines = result.stdout.strip().splitlines()[1:]
    for line in lines:
        if "\tdevice" in line:
            return line.split("\t", 1)[0]
    return None


def _png_size(path):
    # PNG: width/height stored in IHDR, bytes 16..23 (big-endian)
    with open(path, "rb") as f:
        header = f.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    w = int.from_bytes(header[16:20], "big")
    h = int.from_bytes(header[20:24], "big")
    return (w, h)


def main():
    parser = argparse.ArgumentParser(
        description="ADB calibration helper: toggle pointer overlay and capture a screenshot."
    )
    parser.add_argument("--device", default=None, help="ADB device id (serial).")
    parser.add_argument("--pointer", choices=["on", "off"], default=None, help="Toggle pointer_location.")
    parser.add_argument("--show-touches", choices=["on", "off"], default=None, help="Toggle show_touches.")
    parser.add_argument(
        "--out",
        default=None,
        help="Output PNG path (default: ./debug/calibration_<timestamp>.png).",
    )
    args = parser.parse_args()

    device_id = args.device or _default_device_id()
    if not device_id:
        raise SystemExit("No ADB device found. Connect the phone and run `adb devices`.")

    if args.pointer:
        value = "1" if args.pointer == "on" else "0"
        _run(["adb", "-s", device_id, "shell", "settings", "put", "system", "pointer_location", value])

    if args.show_touches:
        value = "1" if args.show_touches == "on" else "0"
        _run(["adb", "-s", device_id, "shell", "settings", "put", "system", "show_touches", value])

    out_path = args.out
    if not out_path:
        os.makedirs("debug", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = os.path.join("debug", f"calibration_{ts}.png")

    result = subprocess.run(
        ["adb", "-s", device_id, "exec-out", "screencap", "-p"],
        capture_output=True,
    )
    if result.returncode != 0:
        raise SystemExit(f"ADB screencap failed: {result.stderr.decode(errors='replace')}")

    with open(out_path, "wb") as f:
        f.write(result.stdout)

    size = _png_size(out_path)
    if size:
        print(f"Saved: {out_path} ({size[0]}x{size[1]})")
    else:
        print(f"Saved: {out_path}")

    print("Tip: enable `--pointer on`, tap a button on the phone, then take another screenshot and read (x,y) from the overlay.")


if __name__ == "__main__":
    main()

