"""
pxl_remap.py provides keyboard-capture remapping for PxlReact.

A remap intercepts a single physical "source" key and, when pressed, sends the first qualifying key
from an ordered sequence. Qualification is driven by a per-entry predicate: a timed sequence uses
per-key cooldown timers, while a pixel-color sequence uses live pixel-color tests.

Capturing (as opposed to sending, which PxlIntercept handles) requires its own Interception context
with a keyboard filter and a blocking await/receive/send loop run on a background thread.
"""

import random
import threading
import time
from dataclasses import dataclass, field

# Local pyinterception clone (do not modify)
import pyinterception.src.interception as pyint
from pyinterception.src.interception.constants import KeyFlag, FilterKeyFlag, MouseFlag, MouseButtonFlag
from pyinterception.src.interception.strokes import KeyStroke, MouseStroke
from pyinterception.src.interception._keycodes import get_key_information

from pxl_keys import DEVICES
from pxl_lib import ColorCondition, PixelMonitor, CastLock
from ansi import *

# Substitute values for Action.key that send a mouse click at the current cursor position
MOUSE_BUTTONS = frozenset( ( 'left', 'right', 'middle' ) )


def _detect_keyboard_index():
    """
    Find the interception device index matching our configured keyboard HWID. Returns the index, or
    None if no match is found (callers should fall back to the context default).
    """
    my_hwid = DEVICES[ 'keyboard' ][ 'handle' ]
    probe = pyint.Interception()
    try:
        idx = 0
        for device in probe.devices:
            hwid = device.get_HWID()
            if hwid is not None and my_hwid in hwid:
                return idx
            idx += 1
    finally:
        probe.destroy()
    return None


def _detect_mouse_index():
    """
    Find the interception device index matching our configured mouse HWID. Returns the index, or
    None if no match is found (callers should fall back to the context default).
    """
    my_hwid = DEVICES[ 'mouse' ][ 'handle' ]
    probe = pyint.Interception()
    try:
        idx = 0
        for device in probe.devices:
            hwid = device.get_HWID()
            if hwid is not None and my_hwid in hwid:
                return idx
            idx += 1
    finally:
        probe.destroy()
    return None


@dataclass
class Action:
    """
    A single game action: a substitute to send (keyboard key or mouse button), gated by an optional
    cooldown and zero or more pixel-color conditions (all of which must hold), with an optional cast
    time during which other actions must not interrupt it.

    For `key`, use a keyboard key name (e.g. "e") or a mouse button: "left", "right", or "middle".
    Mouse substitutes click at the current cursor position without moving the pointer.
    """

    name: str
    key: str
    cooldown: float = 0.0
    cast_time: float = 0.0

    # Color gate: a list of ColorCondition that must ALL hold (logical AND) for the action to fire.
    # An empty list means "no color check"; color_ready short-circuits to True.
    color_checks: list = field( default_factory = list )

    # Last fire time (perf_counter); negative means never fired
    last: float = field( default = -1.0, init = False )

    def cooldown_ready( self ):
        return self.last < 0 or ( time.perf_counter() - self.last ) >= self.cooldown

    def color_ready( self ):
        return all( cond.passes() for cond in self.color_checks )

    def ready( self ):
        return self.cooldown_ready() and self.color_ready()

    def fire( self ):
        self.last = time.perf_counter()

    def describe( self ):
        """Short status string for terminal logging, combining cooldown and color state."""
        if self.cooldown > 0 and self.last >= 0:
            remaining = max( 0.0, self.cooldown - ( time.perf_counter() - self.last ) )
        else:
            remaining = 0.0
        cd = f"{GREEN}rdy{RESET}" if remaining == 0.0 else f"{YELLOW}{remaining:.2f}s{RESET}"

        # One glyph per condition keeps multi-check actions compact in the terminal
        if not self.color_checks:
            color_part = " "
        else:
            color_part = "".join( cond.describe() for cond in self.color_checks )

        return f"{CYAN}{self.name}{RESET} ({MAGENTA}{self.key}{RESET})[{cd}{color_part}]"


class Rotation:
    """
    An ordered list of Actions; resolves to the first ready action.
    """

    def __init__( self, actions ):
        self.actions = actions

    def resolve( self ):
        """Return the first action whose readiness predicate passes, or None."""
        for action in self.actions:
            if action.ready():
                return action
        return None


def _build_color_checks( color_check ):
    """
    Normalize a `color_check` config into a list of ColorCondition (all ANDed at resolve time).

    Accepts either a single condition dict { px, py, color, match? } or a list of such dicts. A
    missing/empty/None value yields an empty list (no color gate). Each condition's `match` defaults
    to True ("pixel must be this color"); set match = False for "pixel must NOT be this color".
    """
    if not color_check:
        return []
    conditions = color_check if isinstance( color_check, list ) else [ color_check ]
    out = []
    for cc in conditions:
        if not cc:
            continue
        out.append(
            ColorCondition(
                px = cc[ 'px' ],
                py = cc[ 'py' ],
                color = cc[ 'color' ],
                match = cc.get( 'match', True ),
            )
        )
    return out


def build_actions( actions_cfg ):
    """
    Build a name -> Action map from an ACTIONS config dict. A missing or empty `color_check` is
    normalized to no color gate (empty condition list).
    """
    out = {}
    for name, c in actions_cfg.items():
        key = c[ 'key' ]
        if key.lower() in MOUSE_BUTTONS:
            key = key.lower()
        out[ name ] = Action(
            name = name,
            key = key,
            cooldown = c.get( 'cooldown', 0.0 ),
            cast_time = c.get( 'cast_time', 0.0 ),
            color_checks = _build_color_checks( c.get( 'color_check' ) ),
        )
    return out


def build_rotations( rotations_cfg, actions ):
    """
    Build a name -> Rotation map. Rotations reference shared Action instances (from `actions`) so
    cooldown state is shared across every rotation that uses a given action.
    """
    rotations = {}
    for rname, seq in rotations_cfg.items():
        resolved = []
        for aname in seq:
            if aname not in actions:
                raise ValueError( f"Rotation '{rname}' references unknown action '{aname}'" )
            resolved.append( actions[ aname ] )
        rotations[ rname ] = Rotation( resolved )
    return rotations


class PxlRemapper:
    """
    Captures keyboard input and remaps configured source keys to sequenced substitutes.

    Driver filters are device-wide, so the entire keyboard is captured; every stroke that is not a
    remapped source (or command hotkey) is re-sent unchanged.

    Substitutes are sent through this same capture context, on the loop thread. Sends from the
    filter-owning context pass downstream without being re-intercepted (the same path as ordinary
    passed-through typing), which is what makes a source-equal substitute such as e -> e work; an
    earlier design sent through a separate context, whose fresh injections WERE re-intercepted and
    swallowed. Sending on the loop thread also avoids racing the device's shared stroke buffer
    against receive().

    This class also owns the application's command hotkeys (formerly the keyboard-library KEYBINDS):
    F12 / ESC quit, and Ctrl+P reports the mouse color. These are intercepted (not forwarded) and
    are not gated by wincheck.
    """

    # Poll interval (ms) for await_input so the loop can observe the stop flag
    AWAIT_TIMEOUT_MS = 500

    # Humanized hold (seconds) for an injected substitute key, mirroring PxlIntercept press delays
    MIN_HOLD = 0.050
    MAX_HOLD = 0.075

    def __init__( self, wincheck, actions, rotations, remaps, on_quit = None, cast_lock = None ):
        """
        Args:
            wincheck (PxlWinCheck): gating; remaps apply only while wincheck.check() returns True.
            actions (dict): ACTIONS config { action_name: { key, cooldown, cast_time, color_check } }
            rotations (dict): ROTATIONS config { rotation_name: [ action_name, ... ] }
            remaps (dict): REMAPS config { source_key_name: rotation_name }
            on_quit (callable | None): invoked when the F12/ESC quit hotkey is pressed.
            cast_lock (CastLock | None): shared cast gate; while active, remap presses are dropped so
                they cannot interrupt a cast. Reactions arm the same lock, so a cast-time reaction is
                protected from remapped keypresses. A private lock is created if none is supplied.
        """
        self.wincheck = wincheck
        self.on_quit = on_quit

        # Shared cast lock: while active(), a cast is in progress and remap presses are dropped so
        # the cast is not interrupted (armed by remap actions with cast_time and by reactions).
        self.cast_lock = cast_lock if cast_lock is not None else CastLock()

        self.ctx = pyint.Interception()
        self.ctx.set_filter( self.ctx.is_keyboard, FilterKeyFlag.FILTER_KEY_ALL )

        idx = _detect_keyboard_index()
        if idx is not None:
            self.ctx.keyboard = idx
            print( f"ℹ️ {GREEN}PxlRemapper{RESET}: capturing keyboard device {MAGENTA}{idx}{RESET}" )
        else:
            print( f"⚠️ {YELLOW}PxlRemapper: keyboard HWID not matched; using default device "
                   f"{MAGENTA}{self.ctx.keyboard}{RESET}" )

        midx = _detect_mouse_index()
        if midx is not None:
            self.ctx.mouse = midx
            print( f"ℹ️ {GREEN}PxlRemapper{RESET}: mouse device {MAGENTA}{midx}{RESET}" )
        else:
            print( f"⚠️ {YELLOW}PxlRemapper: mouse HWID not matched; using default device "
                   f"{MAGENTA}{self.ctx.mouse}{RESET}" )

        # Command hotkey scan codes; ctrl shares scan 0x1D for both left/right (E0 distinguishes)
        self._sc_esc = get_key_information( 'esc' ).scan_code
        self._sc_f12 = get_key_information( 'f12' ).scan_code
        self._sc_p = get_key_information( 'p' ).scan_code
        self._sc_ctrl = get_key_information( 'ctrlleft' ).scan_code
        self._ctrl_down = False
        self._p_swallowed = False

        # Ctrl+P toggles this single-pixel screen-discovery monitor
        self._pixel_monitor = PixelMonitor()

        # Build the shared action pool and rotations, then bind source keys to rotations
        action_pool = build_actions( actions )
        rotation_pool = build_rotations( rotations, action_pool )

        # Build source-scancode -> remap lookup, plus per-source down-state for once-per-press
        self.remaps = {}        # scan_code -> ( extended_bool, Rotation, source_name )
        self.down = {}          # scan_code -> bool
        for source_name, rotation_name in remaps.items():
            if rotation_name not in rotation_pool:
                raise ValueError( f"Remap '{source_name}' references unknown rotation '{rotation_name}'" )

            info = get_key_information( source_name )
            self.remaps[ info.scan_code ] = ( info.is_extended, rotation_pool[ rotation_name ], source_name )
            self.down[ info.scan_code ] = False
            print( f"ℹ️ {GREEN}PxlRemapper{RESET}: bound {CYAN}{source_name}{RESET} "
                   f"(scan {MAGENTA}0x{info.scan_code:02x}{RESET}) -> rotation {MAGENTA}{rotation_name}{RESET}" )

        self._stop_event = threading.Event()
        self._thread = None
        self.start()

    def start( self ):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread( target = self._run, name = 'PxlRemapper', daemon = True )
        self._thread.start()

    def stop( self ):
        print( f"ℹ️ {YELLOW}Closing PxlRemapper...{RESET}" )
        self._stop_event.set()
        self._pixel_monitor.stop()
        if self._thread:
            self._thread.join( timeout = 2.0 )
        try:
            self.ctx.destroy()
        except Exception:
            pass

    def _match( self, stroke ):
        """
        Return ( scan_code, extended, remap, source_name ) if the stroke matches a remapped source,
        else None.
        """
        entry = self.remaps.get( stroke.code )
        if entry is None:
            return None

        extended, remap, source_name = entry
        stroke_extended = bool( stroke.flags & KeyFlag.KEY_E0 )
        if stroke_extended != extended:
            return None

        return stroke.code, extended, remap, source_name

    def _run( self ):
        try:
            while not self._stop_event.is_set():
                device = self.ctx.await_input( self.AWAIT_TIMEOUT_MS )
                if device is None:
                    continue

                stroke = self.ctx.devices[ device ].receive()
                if stroke is None:
                    continue

                # Only keyboard strokes are filtered; anything else passes straight through
                if not isinstance( stroke, KeyStroke ):
                    self.ctx.send( device, stroke )
                    continue

                # Command hotkeys (quit / report color) take precedence and are not gated
                if self._handle_command( device, stroke ):
                    continue

                match = self._match( stroke )
                if match is None:
                    # Not a remapped key; re-send unchanged so normal typing is preserved
                    self.ctx.send( device, stroke )
                    continue

                scan_code, _extended, rotation, source_name = match
                is_up = bool( stroke.flags & KeyFlag.KEY_UP )

                if is_up:
                    # Release of a remapped source; reset down-state and swallow
                    self.down[ scan_code ] = False
                    continue

                if self.down[ scan_code ]:
                    # Auto-repeat while held; ignore until released (once-per-press)
                    continue

                self.down[ scan_code ] = True

                if not self.wincheck.check():
                    # Outside the target app: behave like the real key
                    self.ctx.send( device, stroke )
                    print( f"{CYAN}{source_name}{RESET} {YELLOW}inactive{RESET} -> passthrough" )
                    continue

                if self.cast_lock.active():
                    # A cast is in progress; drop this press so the cast is not interrupted.
                    # FUTURE: to queue instead of dropping, buffer ( source_name, rotation ) here
                    # and flush at cast-end by shrinking the await_input timeout to wake the loop
                    # when the cast elapses, then resolve/fire each buffered press in order.
                    print( f"{CYAN}{source_name}{RESET} {YELLOW}casting{RESET} -> dropped" )
                    continue

                self._fire( source_name, rotation )
        except Exception as exc:
            print( f"{RED}PxlRemapper loop error: {exc}{RESET}" )
        finally:
            try:
                self.ctx.destroy()
            except Exception:
                pass

    def _handle_command( self, device, stroke ):
        """
        Handle the application's command hotkeys. Returns True if the stroke was consumed (and must
        not be processed further); ctrl is forwarded so it still works for the focused app, while
        quit / report-color keys are swallowed.
        """
        is_up = bool( stroke.flags & KeyFlag.KEY_UP )
        code = stroke.code

        # Track (and forward) ctrl so Ctrl+P can be detected without breaking normal ctrl usage
        if code == self._sc_ctrl:
            self._ctrl_down = not is_up
            self.ctx.send( device, stroke )
            return True

        # F12 / ESC quit; swallow both edges so the keys never reach the app
        if code == self._sc_f12:
            if not is_up:
                print( f"⏹️ {RED}quit hotkey{RESET}" )
                if self.on_quit is not None:
                    self.on_quit()
            return True

        # Ctrl+P -> toggle the pixel monitor (reports the pixel under the cursor when its color
        # changes, until Ctrl+P is pressed again)
        if code == self._sc_p and ( self._ctrl_down or self._p_swallowed ):
            if not is_up:
                self._p_swallowed = True
                self._pixel_monitor.toggle()
            else:
                self._p_swallowed = False
            return True

        return False

    def _press_substitute( self, key ):
        """
        Inject a single press of `key` through the capture context.

        `key` may be a keyboard key name or a mouse button (left / right / middle). Keyboard
        substitutes use KeyStrokes on ctx.keyboard; mouse substitutes send button down/up on
        ctx.mouse at the current cursor position (no pointer move). Modifier-bearing keyboard
        substitutes are not supported; game remaps use bare keys or mouse buttons.
        """
        hold = random.uniform( self.MIN_HOLD, self.MAX_HOLD )
        btn = key.lower()
        if btn in MOUSE_BUTTONS:
            down_flag, up_flag = MouseButtonFlag.from_string( btn )
            self.ctx.send( self.ctx.mouse,
                           MouseStroke( MouseFlag.MOUSE_MOVE_ABSOLUTE, down_flag, 0, 0, 0 ) )
            time.sleep( hold )
            self.ctx.send( self.ctx.mouse,
                           MouseStroke( MouseFlag.MOUSE_MOVE_ABSOLUTE, up_flag, 0, 0, 0 ) )
            return

        info = get_key_information( key )

        down = KeyStroke( info.scan_code, KeyFlag.KEY_DOWN )
        up = KeyStroke( info.scan_code, KeyFlag.KEY_UP )
        if info.is_extended:
            down.flags |= KeyFlag.KEY_E0
            up.flags |= KeyFlag.KEY_E0

        self.ctx.send( self.ctx.keyboard, down )
        time.sleep( hold )
        self.ctx.send( self.ctx.keyboard, up )

    def _fire( self, source_name, rotation ):
        """
        Resolve the rotation and send the chosen action's key (if any), with terminal diagnostics.
        An action with a cast_time arms the global cast lock so subsequent presses are dropped until
        the cast completes.
        """
        states = " ".join( a.describe() for a in rotation.actions )
        action = rotation.resolve()

        if action is None:
            print( f"{BLUE}🖮 got {RED}{source_name}{RESET} | {states} | {BLUE}🖮 sent {YELLOW}none{RESET}" )
            return

        self._press_substitute( action.key )
        action.fire()

        if action.cast_time > 0:
            self.cast_lock.arm( action.cast_time )

        print( f"{BLUE}🖮 got {RED}{source_name}{RESET} | {states} | {BLUE}🖮 sent {RED}{action.key}{RESET}" )
