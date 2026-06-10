"""
tgtfoa.py - Toggleable auto-jump and similar convenience features.
"""
import threading
import time

import pyinterception.src.interception as pyint

from ansi import *

AUTO_JUMP_INTERVAL = 0.66

_auto_jump_active = False
_auto_jump_stop = threading.Event()
_auto_jump_thread = None


def _auto_jump_loop( pi ):
    while not _auto_jump_stop.wait( AUTO_JUMP_INTERVAL ):
        pi.press( "alt" )


def toggle_auto_jump( app ):
    """Toggle auto-jump mode: presses the configured key on an interval when on. Bound to CTRL-J in pxlreactHL."""
    global _auto_jump_active, _auto_jump_stop, _auto_jump_thread

    _auto_jump_active = not _auto_jump_active

    if _auto_jump_active:
        _auto_jump_stop.clear()
        _auto_jump_thread = threading.Thread(
            target = _auto_jump_loop,
            args = ( app.PI, ),
            daemon = True
        )
        _auto_jump_thread.start()
        print( f"{GREEN}Auto-jump ON{RESET}" )
    else:
        _auto_jump_stop.set()
        _auto_jump_thread = None
        print( f"{YELLOW}Auto-jump OFF{RESET}" )


# --- Strafe + occasional jump (hold / hold / press on a timer) ---

STRAFE_MOVE_DURATION = 3.0
STRAFE_MOVE_KEYS = ( "a", "d" )
STRAFE_JUMP_KEY = "space"
STRAFE_JUMP_FREQUENCY = 7.0

_strafe_jump_active = False
_strafe_jump_stop = threading.Event()
_strafe_jump_threads = []


def _strafe_loop( move_keys, move_duration, stop_event ):
    if not move_keys:
        return
    n = len( move_keys )
    i = 0
    while not stop_event.is_set():
        key = move_keys[ i % n ]
        i += 1
        pyint.key_down( key, delay = 0 )
        end = time.monotonic() + move_duration
        while time.monotonic() < end:
            if stop_event.wait( 0.05 ):
                pyint.key_up( key, delay = 0 )
                return
        pyint.key_up( key, delay = 0 )


def _jump_loop( pi, jump_key, jump_frequency, stop_event ):
    while not stop_event.wait( jump_frequency ):
        pi.press( jump_key )


def _strafe_jump_worker( pi, move_keys, move_duration, jump_key, jump_frequency, stop_event ):
    t_strafe = threading.Thread(
        target = _strafe_loop,
        args = ( move_keys, move_duration, stop_event ),
        daemon = True
    )
    t_jump = threading.Thread(
        target = _jump_loop,
        args = ( pi, jump_key, jump_frequency, stop_event ),
        daemon = True
    )
    t_strafe.start()
    t_jump.start()
    t_strafe.join()
    t_jump.join()


def toggle_strafe_jump(
    app,
    move_duration = STRAFE_MOVE_DURATION,
    move_keys = STRAFE_MOVE_KEYS,
    jump_key = STRAFE_JUMP_KEY,
    jump_frequency = STRAFE_JUMP_FREQUENCY,
):
    """
    Toggle strafe + occasional jump: cycles through move_keys, holding each for move_duration
    seconds, while a second loop presses jump_key every jump_frequency seconds. Runs until toggled off.
    """
    global _strafe_jump_active, _strafe_jump_stop, _strafe_jump_threads

    _strafe_jump_active = not _strafe_jump_active

    if _strafe_jump_active:
        _strafe_jump_stop.clear()
        mk = tuple( move_keys )
        t = threading.Thread(
            target = _strafe_jump_worker,
            args = (
                app.PI,
                mk,
                move_duration,
                jump_key,
                jump_frequency,
                _strafe_jump_stop,
            ),
            daemon = True
        )
        _strafe_jump_threads = [ t ]
        t.start()
        print(
            f"{GREEN}Strafe+jump ON{RESET} "
            f"keys={CYAN}{mk}{RESET} hold={MAGENTA}{move_duration}s{RESET} "
            f"jump={CYAN}{jump_key}{RESET} every {MAGENTA}{jump_frequency}s{RESET}"
        )
    else:
        _strafe_jump_stop.set()
        _strafe_jump_threads = []
        print( f"{YELLOW}Strafe+jump OFF{RESET}" )
