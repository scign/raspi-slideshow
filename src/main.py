import threading
import time
import signal
import sys
from pathlib import Path
import logging
from shutil import which

from images import set_provider, get_image
from display import display_image, cleanup
from touch import TouchState, get_screen_y_max, monitor_touch

CHANGE_SECONDS = 30
IMAGE_PATH = Path("slideshow.jpg")
TOUCH_DEVICE = '/dev/input/event0'
LOG_PATH = "slideshow.log"

def setup_logging(log_path):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(module)s - %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler()
        ]
    )

def check_system_commands():
    for cmd in ['fbi', 'killall']:
        if which(cmd) is None:
            logging.error(f"Required command '{cmd}' not found in PATH. Exiting.")
            sys.exit(1)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

def main():
    setup_logging(LOG_PATH)
    check_system_commands()
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Choose your provider: 'nasa' or 'google_photos'
    set_provider('nasa')

    screen_y_max = get_screen_y_max(TOUCH_DEVICE)
    touch_state = TouchState()
    touch_thread = threading.Thread(
        target=monitor_touch,
        args=(touch_state, TOUCH_DEVICE, screen_y_max),
        daemon=True
    )
    touch_thread.start()

    # Preload the first image
    try:
        img_bytes = get_image()
        IMAGE_PATH.write_bytes(img_bytes)
    except Exception as e:
        logging.error(f"Startup error: {e}")
        return

    while not touch_state.exit:
        display_image(IMAGE_PATH)

        start_time = time.monotonic()
        while (time.monotonic() - start_time) < CHANGE_SECONDS:
            if touch_state.exit:
                break
            if touch_state.skip:
                touch_state.skip = False
                break
            time.sleep(0.1)

        if not touch_state.exit:
            try:
                img_bytes = get_image()
                if img_bytes:
                    IMAGE_PATH.write_bytes(img_bytes)
                else:
                    logging.warning("Failed to get next image, will try again.")
            except Exception as e:
                logging.error(f"Image retrieval error: {e}")

    cleanup()
    logging.info("Exiting slideshow.")

if __name__ == '__main__':
    main()

