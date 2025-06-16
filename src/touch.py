from evdev import InputDevice, ecodes
import logging

class TouchState:
    def __init__(self):
        self.skip = False
        self.exit = False

def get_screen_y_max(touch_device):
    try:
        dev = InputDevice(touch_device)
        absinfo = dev.absinfo(ecodes.ABS_Y)
        logging.info(f"Detected touchscreen Y axis max: {absinfo.max}")
        return absinfo.max
    except Exception as e:
        logging.warning(f"Error detecting touchscreen max Y: {e}")
        return 4095

def monitor_touch(touch_state, touch_device, screen_y_max):
    dev = InputDevice(touch_device)
    y = None
    for event in dev.read_loop():
        if event.type == ecodes.EV_ABS and event.code == ecodes.ABS_Y:
            y = event.value
        elif (
            event.type == ecodes.EV_KEY
            and event.code == ecodes.BTN_LEFT
            and event.value == 1
            and y is not None
        ):
            if y < screen_y_max / 2:
                logging.info(f"Touch at Y={y} (top half): skipping to next image.")
                touch_state.skip = True
            else:
                logging.info(f"Touch at Y={y} (bottom half): exiting slideshow.")
                touch_state.exit = True
            y = None
