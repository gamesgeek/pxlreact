"""
pxl_scan is a module designed to help the user experiment with different methods of searching for
images or "sequences" of pixels at various screen locations.

It is loosely related to the pxlreact project and should benefit from the utilities elsewhere, but
it is not intended to be integrated into the project as a whole or to provide functionality
to other modules.
"""

import keyboard
import threading
import time
from PIL import Image

from pxl_lib import get_pixel_color, colors_similar
from pxl_keys import DEVICES
from ansi import *

import pyinterception.src.interception as pyint

# Initialize mouse device from known hardware
_mouse_hwid = DEVICES['mouse']['handle']
for _idx, _device in enumerate( pyint.Interception().devices ):
    _hwid = _device.get_HWID()
    if _hwid is not None and _mouse_hwid in _hwid:
        pyint.set_devices( mouse = _idx )
        break

# The color we expect to be present at one of four possible positions
dark_gray = (88, 85, 81)
light_gray = (131, 125, 134)

def find_target_color( y = 706 ):
    """
    Super "dumb" search that looks at four predefined hard-coded positions and returns the
    first to match the target color. If found, moves the mouse to that position.
    """
    for x in [ 118, 335, 552, 774 ]:
        pxl_color = get_pixel_color( x, y )
        pxl_grey = colors_similar( pxl_color, dark_gray ) or colors_similar( pxl_color, light_gray )
        if pxl_grey:
            print( f"{GREEN}Found target at ({MAGENTA}{x}{GREEN}, {MAGENTA}{y}{GREEN}) - clicking{RESET}" )
            pyint.move_to( x, y )
            pyint.mouse_down( "left", delay = 0 )
            pyint.mouse_up( "left", delay = 0 )
            # delay 200ms after each click to avoid "spam" clicking
            time.sleep( 0.5 )
            return x, y
    print( f"{YELLOW}No target color found at y={y}{RESET}" )
    return None


# Continuous mode state
_continuous_active = False
_continuous_thread = None


def _continuous_loop():
    """
    Background loop that repeatedly calls find_target_color while continuous mode is active.
    """
    global _continuous_active

    while _continuous_active:
        find_target_color( y = 706 )
        time.sleep( 0.1 )


def toggle_continuous():
    """
    Toggle continuous scanning mode on/off. Runs in a background thread to avoid blocking input.
    """
    global _continuous_active, _continuous_thread

    if _continuous_active:
        _continuous_active = False
        print( f"{RED}Continuous mode OFF{RESET}" )
    else:
        _continuous_active = True
        print( f"{GREEN}Continuous mode ON{RESET}" )
        _continuous_thread = threading.Thread( target = _continuous_loop, daemon = True )
        _continuous_thread.start()


KEYBINDS = {
    "ctrl+l": lambda: find_target_color( y = 706 ),
    "ctrl+shift+l": toggle_continuous
}


def start_scan_listener():
    """
    Register keybinds and block until the user presses ESC to exit.
    """
    global _continuous_active

    for key_combo, action in KEYBINDS.items():
        keyboard.add_hotkey( key_combo, action )

    print( f"{CYAN}pxl_scan{RESET} listening..." )
    print( f"  {YELLOW}CTRL+L{RESET} single search | {YELLOW}CTRL+SHIFT+L{RESET} toggle continuous | {RED}ESC{RESET} exit" )
    keyboard.wait( "esc" )
    _continuous_active = False
    keyboard.unhook_all()
    print( f"{RED}Exiting pxl_scan{RESET}" )


if __name__ == "__main__":
    start_scan_listener()
