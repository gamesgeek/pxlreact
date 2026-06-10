"""
test_remap.py is a standalone harness for validating PxlRemapper without the full PxlReact app.

It wires a PxlRemapper to a stub window-watch that is always active, so remaps fire regardless of
the focused window. This makes it easy to validate in a scratch buffer.

Usage:
    1. Activate the venv:  .pxlenv\\Scripts\\Activate.ps1
    2. Run:                python test_remap.py
    3. Open a text editor (e.g. Notepad) and give it focus.
    4. Tap the source key 'e' repeatedly. Each discrete press sends the first ready key from the
       timed sequence: 'r' (3.25s), 'f' (6.33s), 'e' (2.2s). Holding 'e' does NOT auto-repeat;
       release and press again to fire once more. The 'e' -> 'e' case now types 'e' in the editor.
    5. Watch this terminal: each press prints the source, every entry's cooldown state, and the
       chosen key (GREEN) or a no-candidate notice (YELLOW).
    6. Press Ctrl+P to print the mouse color (intercepted; the 'p' is not typed in the editor).
    7. Press ESC or F12 to quit.

Pixel sequence:
    The 'q' bind uses placeholder coordinates/colors that almost certainly will not match your
    screen (so it will report "no candidate"). To exercise it, capture real values first with
    pxl_lib.report_mouse_color(), drop them into PIXEL_BIND below, and re-run.

Expected output (timed, abbreviated):
    ⌨️ e | fireball->r [rdy] volcano->f [rdy] ember->e [rdy] | sent r
    ⌨️ e | fireball->r [3.10s] volcano->f [6.18s] ember->e [rdy] | sent e
    ⌨️ e | fireball->r [2.95s] volcano->f [6.03s] ember->e [1.85s] | no candidate
"""

import threading

from pxl_remap import PxlRemapper
from ansi import *


# Always-active stand-in for PxlWinWatch so remaps fire without the target app
class StubWinWatch:
    active = True


TIMED_BIND = ( "timed", {
    "fireball": { "key": "r", "timeout": 3.25 },
    "volcano":  { "key": "f", "timeout": 6.33 },
    "ember":    { "key": "e", "timeout": 2.2 },
} )

PIXEL_BIND = ( "pixel", {
    "fireball": { "key": "r", "px": 2452, "py": 94, "color": (65, 67, 57) },
    "volcano":  { "key": "f", "px": 1726,  "py": 1363,  "color": (62, 69, 44) },
} )

REMAPS = {
    "e": TIMED_BIND,
    "q": PIXEL_BIND,
}


def main():
    stop = threading.Event()
    remapper = PxlRemapper( StubWinWatch(), REMAPS, on_quit = stop.set )

    print( f"{GREEN}test_remap running{RESET}: tap {CYAN}e{RESET} (timed) or {CYAN}q{RESET} (pixel) "
           f"in a text editor; {CYAN}Ctrl+P{RESET} reports color; {CYAN}ESC/F12{RESET} to quit." )

    try:
        stop.wait()
    except KeyboardInterrupt:
        pass
    finally:
        remapper.stop()
        print( f"{YELLOW}test_remap stopped.{RESET}" )


if __name__ == "__main__":
    main()
