import threading
import time
import signal
import sys
from pathlib import Path
import logging
from shutil import which

from images import get_image
from display import display_image, cleanup
from touch import TouchState, get_screen_y_max, monitor_touch

CHANGE_SECONDS = 10
IMAGE_PATH_TMP = Path("/tmp/slidehow_image.jpg")
NEXT_IMAGE_PATH_TMP = Path("/tmp/slideshow_image_next.jpg")
TOUCH_DEVICE = '/dev/input/event0'
LOG_PATH = "/tmp/slideshow.log"

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

    screen_y_max = get_screen_y_max(TOUCH_DEVICE)
    touch_state = TouchState()
    touch_thread = threading.Thread(target=monitor_touch, args=(touch_state, TOUCH_DEVICE, screen_y_max), daemon=True)
    touch_thread.start()

    # Preload the first image
    try:
        img_bytes = get_image()
        IMAGE_PATH_TMP.write_bytes(img_bytes)
    except Exception as e:
        logging.error(f"Startup error: {e}")
        return

    while not touch_state.exit:
        display_image(IMAGE_PATH_TMP)
        # Preload next image in background
        next_downloaded = False
        def preload_next():
            nonlocal next_downloaded
            try:
                next_img_bytes = get_image()
                NEXT_IMAGE_PATH_TMP.write_bytes(next_img_bytes)
                next_downloaded = True
            except Exception as e:
                logging.error(f"Preload error: {e}")

        preload_thread = threading.Thread(target=preload_next)
        preload_thread.start()

        # Wait with skip/exit check
        waited = 0
        while waited < CHANGE_SECONDS:
            if touch_state.exit:
                break
            if touch_state.skip:
                touch_state.skip = False
                break
            time.sleep(0.1)
            waited += 0.1

        preload_thread.join()  # Ensure next image is ready

        # Move preloaded image to current, or try again if failed
        if not touch_state.exit:
            if next_downloaded:
                IMAGE_PATH_TMP.write_bytes(NEXT_IMAGE_PATH_TMP.read_bytes())
            else:
                logging.warning("Failed to preload next image, will try again.")

    cleanup()
    logging.info("Exiting slideshow.")

if __name__ == '__main__':
    main()

