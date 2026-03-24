#!/usr/bin/env python3
"""
Mac Battery Life Test
=====================
Workflow:
  1. Max screen brightness
  2. Prevent display/system sleep (caffeinate)
  3. Set volume to 50 %
  4. Open Zoom → New Meeting (camera + mic + screen share)
  5. Every INTERVAL_MIN minutes: open URLS_PER_INTERVAL web pages
     and EXCEL_PER_INTERVAL large Excel files
  6. Run for TEST_DURATION_MIN minutes
  7. Log battery level every minute; print summary at end

Usage:
    pip install openpyxl          # one-time setup
    python bltest.py
"""

import datetime
import logging
import os
import random
import re
import string
import subprocess
import sys
import threading
import time
import webbrowser

# ─── Configuration ────────────────────────────────────────────────────────────

TEST_DURATION_MIN  = 60
INTERVAL_MIN       = 10
URLS_PER_INTERVAL  = 15
EXCEL_PER_INTERVAL = 3
EXCEL_ROWS         = 10_000   # ~3-5 MB per file
EXCEL_COLS         = 30
VOLUME_PERCENT     = 50

URLS = [
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    "https://www.google.com/search?q=battery+life+benchmark",
    "https://github.com/trending",
    "https://stackoverflow.com/questions",
    "https://www.reddit.com/r/technology",
    "https://x.com/explore",
    "https://www.facebook.com",
    "https://www.instagram.com/explore",
    "https://www.linkedin.com/feed",
    "https://www.amazon.com/bestsellers",
    "https://www.netflix.com/browse",
    "https://www.apple.com/mac",
    "https://www.microsoft.com",
    "https://en.wikipedia.org/wiki/Special:Random",
    "https://www.cnn.com",
]

# ─── Logging setup ────────────────────────────────────────────────────────────

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE  = os.path.join(
    _BASE_DIR,
    f"battery_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ─── System helpers ───────────────────────────────────────────────────────────


def _osascript(script: str) -> str:
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    return result.stdout.strip()


def get_battery_info() -> dict:
    """Return battery percentage, charging state, and time remaining."""
    try:
        raw = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        pct_m   = re.search(r"(\d+)%", raw)
        time_m  = re.search(r"(\d+:\d+) remaining", raw)
        pct       = int(pct_m.group(1)) if pct_m else -1
        remaining = time_m.group(1) if time_m else "unknown"
        charging  = "discharging" not in raw.lower()
        return {"percent": pct, "charging": charging, "remaining": remaining, "raw": raw.strip()}
    except Exception as exc:
        return {"percent": -1, "charging": False, "remaining": "unknown", "raw": str(exc)}


def set_max_brightness() -> None:
    """Press the hardware brightness-up key 32 times to reach maximum."""
    log.info("Setting screen brightness to maximum…")

    # Method 1: try the `brightness` CLI tool (brew install brightness)
    if subprocess.run(["which", "brightness"], capture_output=True).returncode == 0:
        subprocess.run(["brightness", "1"], capture_output=True)
        log.info("Brightness set via `brightness` CLI.")
        return

    # Method 2: key-press simulation (works on most Mac keyboards)
    _osascript(
        """
        tell application "System Events"
            repeat 32 times
                key code 144
                delay 0.04
            end repeat
        end tell
        """
    )
    log.info("Brightness key pressed 32× (should be at max).")


def set_volume(pct: int) -> None:
    log.info(f"Setting system volume to {pct}%…")
    _osascript(f"set volume output volume {pct}")


def start_caffeinate() -> subprocess.Popen:
    """Prevent display sleep (-d), idle sleep (-i), and system sleep (-s)."""
    log.info("Starting caffeinate to prevent sleep…")
    return subprocess.Popen(["caffeinate", "-d", "-i", "-s"])


# ─── Zoom ─────────────────────────────────────────────────────────────────────


def open_zoom_meeting() -> None:
    """Launch Zoom and attempt to start a New Meeting via accessibility."""
    log.info("Launching Zoom…")
    subprocess.run(["open", "-a", "zoom.us"], capture_output=True)
    time.sleep(5)

    # Try clicking "New Meeting" button via Accessibility API
    _osascript(
        """
        tell application "zoom.us" to activate
        delay 2
        tell application "System Events"
            tell process "zoom.us"
                try
                    click button "New Meeting" of window 1
                end try
            end tell
        end tell
        """
    )

    log.info("")
    log.info("┌─────────────────────────────────────────────┐")
    log.info("│  ACTION REQUIRED — Please do in Zoom:       │")
    log.info("│  1. Click 'New Meeting' (if not auto-done)  │")
    log.info("│  2. Enable Camera & Microphone              │")
    log.info("│  3. Start Screen Share → choose full screen │")
    log.info("└─────────────────────────────────────────────┘")
    log.info("Waiting 30 s for Zoom setup…")
    time.sleep(30)


# ─── Excel ────────────────────────────────────────────────────────────────────


def _ensure_openpyxl() -> None:
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        log.info("openpyxl not found — installing…")
        subprocess.run([sys.executable, "-m", "pip", "install", "openpyxl"], check=True)


def create_large_excel(filepath: str) -> bool:
    """Create a large xlsx file with EXCEL_ROWS rows × EXCEL_COLS columns."""
    log.info(f"  Generating {EXCEL_ROWS:,} rows × {EXCEL_COLS} cols → {os.path.basename(filepath)}")
    try:
        from openpyxl import Workbook

        wb = Workbook(write_only=True)
        ws = wb.create_sheet("BattTestData")

        # Header
        ws.append([f"Column_{c}" for c in range(1, EXCEL_COLS + 1)])

        # Data rows with mixed types for file weight
        for _ in range(EXCEL_ROWS):
            row = []
            for c in range(EXCEL_COLS):
                r = c % 4
                if r == 0:
                    row.append(round(random.uniform(0, 1_000_000), 4))
                elif r == 1:
                    row.append(random.randint(0, 9_999_999))
                elif r == 2:
                    row.append("".join(random.choices(string.ascii_letters + string.digits, k=14)))
                else:
                    row.append(
                        datetime.datetime(
                            random.randint(2000, 2025),
                            random.randint(1, 12),
                            random.randint(1, 28),
                        )
                    )
            ws.append(row)

        wb.save(filepath)
        return True

    except Exception as exc:
        log.error(f"Excel generation failed: {exc}")
        return False


def prepare_excel_files() -> list:
    """Pre-generate Excel test files, skip existing ones. Returns list of paths."""
    excel_dir = os.path.join(_BASE_DIR, "excel_test_files")
    os.makedirs(excel_dir, exist_ok=True)

    paths = []
    for i in range(1, EXCEL_PER_INTERVAL + 1):
        fp = os.path.join(excel_dir, f"large_test_{i}.xlsx")
        if os.path.exists(fp):
            log.info(f"  Excel file {i} already exists, reusing.")
        else:
            create_large_excel(fp)
        paths.append(fp)

    return paths


# ─── Burst actions ────────────────────────────────────────────────────────────


def open_web_pages(urls: list) -> None:
    log.info(f"  Opening {len(urls)} web pages…")
    for url in urls:
        webbrowser.open_new_tab(url)
        time.sleep(0.35)


def open_excel_files(paths: list) -> None:
    log.info(f"  Opening {len(paths)} Excel files…")
    for p in paths:
        subprocess.run(["open", p])
        time.sleep(0.8)


# ─── Battery monitor thread ───────────────────────────────────────────────────


def _battery_monitor(stop: threading.Event, interval_sec: int = 60) -> None:
    while not stop.is_set():
        info = get_battery_info()
        state = "charging" if info["charging"] else "discharging"
        log.info(
            f"[BATTERY] {info['percent']:>3}%  remaining={info['remaining']}  {state}"
        )
        stop.wait(interval_sec)


# ─── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    log.info("=" * 64)
    log.info("  Mac Battery Life Test")
    log.info(f"  Duration: {TEST_DURATION_MIN} min | Interval: {INTERVAL_MIN} min")
    log.info(f"  URLs/burst: {URLS_PER_INTERVAL} | Excel/burst: {EXCEL_PER_INTERVAL}")
    log.info(f"  Log → {LOG_FILE}")
    log.info("=" * 64)

    _ensure_openpyxl()

    # ── Initial battery check ──────────────────────────────────────
    init_info = get_battery_info()
    log.info(f"Initial battery: {init_info['percent']}%  |  {init_info['raw'].splitlines()[0]}")

    if init_info["charging"]:
        log.warning("WARNING: Device is charging. Unplug the power adapter for an accurate test.")
        input("Press Enter after unplugging (or Enter to continue anyway)… ")

    # ── System setup ──────────────────────────────────────────────
    set_max_brightness()
    set_volume(VOLUME_PERCENT)
    caffeinate_proc = start_caffeinate()

    # ── Zoom ──────────────────────────────────────────────────────
    open_zoom_meeting()

    # ── Prepare Excel files ───────────────────────────────────────
    log.info("Preparing large Excel files…")
    excel_files = prepare_excel_files()
    log.info(f"Excel files ready: {len(excel_files)} file(s)")

    # ── Start battery monitor thread ──────────────────────────────
    stop_event = threading.Event()
    monitor = threading.Thread(
        target=_battery_monitor, args=(stop_event, 60), daemon=True
    )
    monitor.start()

    # ── Main test loop ────────────────────────────────────────────
    total_intervals = TEST_DURATION_MIN // INTERVAL_MIN
    log.info(f"\nTest started — {total_intervals} bursts planned over {TEST_DURATION_MIN} min\n" + "─" * 64)

    test_start = time.time()
    try:
        for burst_n in range(1, total_intervals + 1):
            # Wait until the next interval mark
            target = test_start + burst_n * INTERVAL_MIN * 60
            wait_sec = target - time.time()
            if wait_sec > 0:
                log.info(
                    f"Next burst #{burst_n}/{total_intervals} in {wait_sec:.0f} s…"
                )
                time.sleep(wait_sec)

            elapsed_min = (time.time() - test_start) / 60
            info = get_battery_info()
            log.info("─" * 64)
            log.info(
                f"BURST {burst_n}/{total_intervals}  |  "
                f"Elapsed: {elapsed_min:.1f} min  |  Battery: {info['percent']}%"
            )
            log.info("─" * 64)

            open_web_pages(URLS[:URLS_PER_INTERVAL])
            open_excel_files(excel_files)

    except KeyboardInterrupt:
        log.info("\nTest interrupted by user (Ctrl-C).")

    finally:
        stop_event.set()
        caffeinate_proc.terminate()

        elapsed_min  = (time.time() - test_start) / 60
        final_info   = get_battery_info()
        consumed     = init_info["percent"] - final_info["percent"]

        log.info("=" * 64)
        log.info(f"Test finished.  Elapsed: {elapsed_min:.1f} min")
        log.info(
            f"Battery:  start={init_info['percent']}%  →  end={final_info['percent']}%  "
            f"(consumed {consumed}%)"
        )
        if elapsed_min > 0 and consumed > 0:
            projected_h = (100 / consumed) * (elapsed_min / 60)
            log.info(f"Projected full-charge life: ~{projected_h:.1f} h  (under this workload)")
        log.info(f"Full log saved to: {LOG_FILE}")
        log.info("=" * 64)


if __name__ == "__main__":
    main()
