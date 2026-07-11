"""
pxlreactHL.py is a variant of the PxlReact project which strips the tkinter GUI elements and uses a
lighter weight command line interface.

This is the project's main module which is responsible for assigning reactions to pixels and then
polling those pixels for changes.
"""
import ctypes
import json
import os
import time

import threading

from pxl_wincheck import PxlWinCheck
from pxl_intercept import PxlIntercept
from pxl_remap import PxlRemapper

from pxl_lib import *
from ansi import *

from pxl_config import get_settings, load_profile

class PxlReactApp:
    """
    PxlReactApp is the main application class for the PxlReact project; it initializes the GUI and manages the list of
    pixels being monitored (formerly PxlWatcher).
    """

    def __init__( self ):
        """
        Load configuration (settings.toml + profile.json), wire up the subsystems, and create one
        monitored pixel per enabled profile reaction.
        """
        self.settings = get_settings()
        self.profile = load_profile()

        # On-demand window/marker gate; check() is evaluated live at each reaction/remap fire point
        self.wincheck = PxlWinCheck( self.profile[ 'wincheck' ] )

        self.PI = PxlIntercept()

        self.stop_event = threading.Event()

        # Shared cast lock: a cast-time reaction arms it so the remapper drops keypresses that would
        # otherwise interrupt the cast; remap actions with a cast_time arm the same lock.
        self.cast_lock = CastLock()

        # Keyboard-capture remapping layer (starts its own background thread); also owns the
        # F12/ESC quit and Ctrl+P report-color command hotkeys
        self.remapper = PxlRemapper( self.wincheck,
                                     self.profile[ 'actions' ],
                                     self.profile[ 'rotations' ],
                                     self.profile[ 'remaps' ],
                                     on_quit = self.exit_application, cast_lock = self.cast_lock )

        self.tick_interval = self.settings[ 'app' ][ 'tick_interval' ]

        self.registry = PxlReactionRegistry( self )

        # One monitored pixel per enabled reaction; no fixed slot count
        self.pixels = []
        for name, data in self.profile[ 'reactions' ].items():
            if data[ 'enabled' ]:
                self.load_reaction( name )

    def start_update_loop( self ):
        """
        Main update loop without GUI. Blocks and polls pixels at the configured interval.
        """
        try:
            while not self.stop_event.is_set():
                # One live gate read per tick; when inactive (wrong window or marker off, e.g. a
                # loading screen) clear pending streaks so a confirmation can't carry across the
                # gap and fire the instant the context returns.
                active = self.wincheck.check()
                for pxl in self.pixels:
                    if active:
                        pxl.update_color()
                    elif pxl.reaction is not None:
                        pxl.reaction.reset()
                if self.registry.trigger_log is not None:
                    self.registry.trigger_log.maybe_save()
                time.sleep( self.tick_interval )
        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            self.cleanup()

    def load_reaction( self, reaction_name ):
        """
        Create a monitored pixel for `reaction_name` at its registry coordinates and attach the
        reaction built by the registry's factory (plain by default; capture mode swaps the factory
        once at startup, so this construction site needs no capture branching).
        """
        reaction_data = self.registry.reactions_registry[ reaction_name ]

        pixel = Pxl( len( self.pixels ) + 1, reaction_data[ 'sx' ], reaction_data[ 'sy' ], app = self )
        pixel.set_reaction(
            self.registry.reaction_factory( pixel, reaction_data, reaction_name,
                                            self.registry.trigger_log, self.cast_lock )
        )
        self.pixels.append( pixel )
        print( f"[{pixel.index}] {BLUE}{reaction_name}{RESET} @ ({reaction_data['sx']}, {reaction_data['sy']})" )

    def exit_application( self ):
        """
        Exit the application cleanly, releasing resources.
        """
        self.stop_event.set()

    def cleanup( self ):
        """
        Clean up resources and background workers. Safe to call multiple times.
        """
        global HDC
        print( f"ℹ️ {RED}Exiting PxlReactApp...{RE}" )

        # Persist and surface accumulated trigger data before tearing down so the user can spot
        # ignorable colors; the forced save guarantees the final session's events reach disk.
        if self.registry.trigger_log is not None:
            try:
                self.registry.trigger_log.save( force = True )
                self.registry.trigger_log.report()
            except Exception:
                pass

        # Capture debug mode (optional): drain/stop the snapshot worker if it was running
        if self.registry.snapshot is not None:
            try:
                self.registry.snapshot.stop()
            except Exception:
                pass

        try:
            self.remapper.stop()
        except Exception:
            pass

        try:
            self.PI.close()
        except Exception:
            pass

        try:
            ctypes.windll.user32.ReleaseDC( 0, HDC )
        except Exception:
            pass


class Pxl:
    """
    One of the pixels being monitored; pixels know about their own color and maintain a flag to let other classes
    know when they have changed color.
    """

    def __init__( self, index, sx = None, sy = None, app = None ):
        """
        Initialize a Pxl instance; initializing a pixel without sx, sy parameters should create a pixel that pays attention
        to the color under the mouse cursor.

        Args:
            index (int): Index of the pixel in the monitoring list.
            sx (int): Screen X-coordinate of the pixel.
            sy (int): Screen Y-coordinate of the pixel.
        """

        self.index = index
        self.sx = sx
        self.sy = sy

        # Let each Pxl keep a reference to its app
        self.app = app

        # Pxl's provide a "single source of truth" for color data; no other classes or methods should need to query
        # screen pixel colors directly on their own.
        self.rgb = None

        self.reaction = None

        # Perform an initial update to set the Pxl's color after assignment or loading from file
        self.update_color()

    def update_color( self ):
        """
        Poll the color at this Pxl's location and tick its reaction's debounce state machine.

        Evaluation runs every poll (not only when the raw color changes) so the reaction can time
        how long an off-color condition has persisted before deciding to fire.
        """

        screen_rgb = get_pixel_color( self.sx, self.sy )

        if screen_rgb:
            self.rgb = screen_rgb

            if self.reaction is not None:
                self.reaction.evaluate()

    def set_reaction( self, pixel_reaction ):
        """
        Assign a reaction to this pixel.

        Args:
            pixel_reaction (PxlReaction): Reaction object defining how this pixel reacts to changes.
        """
        self.reaction = pixel_reaction


class CooldownReadiness:
    """
    Time-based readiness: a reaction is ready again once `cooldown` seconds have elapsed since it
    last fired. Suited to abilities with a fixed, known recharge time (flasks, etc.).
    """

    def __init__( self, cooldown ):
        self.cooldown = cooldown
        self._last = -1.0

    def ready( self ):
        return self._last < 0 or ( time.perf_counter() - self._last ) >= self.cooldown

    def fired( self ):
        self._last = time.perf_counter()


class ColorReadiness:
    """
    Pixel-color readiness: a reaction is ready only while a separate "available" indicator pixel
    (e.g. a skill icon) shows the expected color, judged within this check's own `tolerance`.
    Suited to emergency abilities whose cooldown is too variable to time, but which expose an
    on-screen ready/not-ready indicator.

    A short `lockout` after firing suppresses immediate re-triggering during the brief window before
    the indicator updates to its not-ready color (otherwise the poll loop could fire several times).
    """

    def __init__( self, px, py, color, tolerance, lockout = 0.5 ):
        self.px = px
        self.py = py
        self.color = color
        self.tolerance = tolerance
        self.lockout = lockout
        self._last = -1.0

    def ready( self ):
        if self._last >= 0 and ( time.perf_counter() - self._last ) < self.lockout:
            return False
        observed = get_pixel_color( self.px, self.py )
        return observed is not None and colors_similar( observed, self.color, self.tolerance )

    def fired( self ):
        self._last = time.perf_counter()


class CompositeReadiness:
    """
    Readiness that requires ALL of its sub-strategies to be ready (logical AND). Use to combine, for
    example, a minimum cooldown with a pixel-color availability check, so a reaction fires only once
    the cooldown has elapsed AND the indicator shows the skill is available.
    """

    def __init__( self, strategies ):
        self.strategies = strategies

    def ready( self ):
        return all( s.ready() for s in self.strategies )

    def fired( self ):
        for s in self.strategies:
            s.fired()


class PxlReaction:
    """
    Defines a reaction for a monitored pixel, specifying conditions and behavior when the reaction triggers.

    Whether the reaction may fire is decided by a pluggable readiness strategy (see CooldownReadiness
    and ColorReadiness): the firing CONDITION (react_if_color / react_if_not_color) is independent of
    the readiness/availability gate.
    """

    def __init__( self, pxl, reaction_type, reaction_color, tolerance, reaction, readiness,
                  confirm = 0.0, ignore_colors = None, name = None, trigger_log = None,
                  cast_time = 0.0, cast_lock = None ):
        """
        Initialize a PxlReaction instance.

        Args:
            pixel_index (int): The index of our "parent" Pxl (i.e., the one that determines if we trigger)
            reaction_type (str): Type of reaction; "react_if_not_color" fires when the pixel deviates
                from `reaction_color`, "react_if_color" fires when it matches `reaction_color`.
            reaction_color (tuple[int, int, int]): Target RGB color for the reaction.
            tolerance (int): SSD tolerance for this reaction's color comparisons (firing condition
                and ignore_colors); each reaction carries its own so volatile screen regions can be
                tuned independently.
            reaction (callable): Function to execute when the reaction triggers.
            readiness: A readiness strategy exposing ready()/fired() (CooldownReadiness or
                ColorReadiness). Gates firing on either elapsed time or an availability pixel color.
            confirm (float, optional): Seconds the firing condition must persist before firing;
                filters brief transients (status-effect tints) that clear within a few frames.
                Default 0.0 fires on the first reading (no debounce).
            ignore_colors (list[tuple] | None): For "react_if_not_color", a set of benign off-colors
                (e.g. poison/curse tints) that should NOT trigger; a reading similar to any of these
                is treated as on-color. Tested against the same pixel already read, so the cost is a
                handful of comparisons per tick.
            name (str | None): Registry name of this reaction, used to label trigger-log entries.
            trigger_log (TriggerLog | None): When provided, the color that caused each firing is
                recorded for the post-session report.
            cast_time (float, optional): Seconds this reaction's action takes to cast. When > 0, the
                shared cast_lock is armed on firing so remapped keypresses are dropped and cannot
                interrupt the cast. Default 0.0 (no cast protection).
            cast_lock (CastLock | None): shared cast gate armed when a cast_time reaction fires.
        """
        self.pxl = pxl
        self.type = reaction_type
        self.reaction_color = reaction_color
        self.tolerance = tolerance
        self.readiness = readiness
        self.confirm = confirm
        self.reaction = reaction
        self.ignore_colors = ignore_colors or []
        self.name = name
        self.trigger_log = trigger_log
        self.cast_time = cast_time
        self.cast_lock = cast_lock

        # perf_counter timestamp marking the start of an uninterrupted firing-condition streak; None
        # while the pixel reads as safe. A trigger requires the streak to last at least `confirm`.
        self._pending_since = None

    def _should_fire( self ):
        """
        Instantaneous firing condition for the current reaction type.

        react_if_not_color: the pixel deviates from `reaction_color` AND is not one of the benign
        `ignore_colors` (sustained-but-harmless tints such as poison/curse).
        react_if_color: the pixel matches `reaction_color`.
        """
        rgb = self.pxl.rgb
        if self.type == "react_if_color":
            return colors_similar( rgb, self.reaction_color, self.tolerance )
        # default: react_if_not_color
        return ( colors_different( rgb, self.reaction_color, self.tolerance )
                 and not matches_any( rgb, self.ignore_colors, self.tolerance ) )

    def evaluate( self ):
        """
        Tick the debounce state machine against the pixel's current color. Fires only when the
        firing condition has held continuously for at least `confirm` seconds, so brief transients
        (e.g. shocked/poisoned tints) that clear within a few frames are ignored.

        The caller (poll loop) must only invoke this while the app context is active; reset() drops
        a pending streak when the context goes inactive.
        """
        if not self._should_fire():
            self._pending_since = None
            return

        now = time.perf_counter()
        if self._pending_since is None:
            self._pending_since = now

        if self.readiness.ready() and ( now - self._pending_since ) >= self.confirm:
            self.trigger()
            self._pending_since = None

    def reset( self ):
        """Drop any in-progress confirmation streak (called when the app context is inactive)."""
        self._pending_since = None

    def trigger( self ):
        """
        Call the reaction function and notify the readiness strategy that it fired. The triggering
        pixel color is recorded to the trigger log (when one is attached) before firing.
        """
        if self.trigger_log is not None:
            self.trigger_log.record( self.name, self.pxl.rgb )
        # Arm the cast lock before sending the key so an in-flight remap press can't slip in and
        # interrupt the cast between firing and the lock being set.
        if self.cast_time > 0 and self.cast_lock is not None:
            self.cast_lock.arm( self.cast_time )
        self.reaction()
        self.readiness.fired()


def _build_one_readiness( spec ):
    """Build a single readiness strategy from one normalized `ready` spec dict."""
    if spec[ 'type' ] == 'color':
        return ColorReadiness( spec[ 'px' ], spec[ 'py' ], spec[ 'color' ],
                               spec[ 'tolerance' ], spec[ 'lockout' ] )
    return CooldownReadiness( spec[ 'cooldown' ] )


def build_readiness( data ):
    """
    Construct a reaction's readiness strategy from its registry entry (normalized by pxl_config).

    `ready` is a list of spec dicts that must ALL be ready (AND, via CompositeReadiness): each is
    { 'type': 'color', 'px', 'py', 'color', 'tolerance', 'lockout' } for pixel-color readiness, or
    { 'type': 'cooldown', 'cooldown' } for time readiness. When `ready` is None the `cooldown`
    shorthand is used (time readiness).
    """
    specs = data[ 'ready' ]
    if specs is None:
        return CooldownReadiness( data[ 'cooldown' ] )
    if len( specs ) == 1:
        return _build_one_readiness( specs[ 0 ] )
    return CompositeReadiness( [ _build_one_readiness( s ) for s in specs ] )


def build_reaction( pixel, data, name, trigger_log, cast_lock ):
    """
    Default reaction factory: a plain, capture-free PxlReaction. The registry holds a reference to a
    factory with this signature so the construction site stays branch-free; capture mode swaps in a
    different factory (see pxl_capture.make_capturing_factory) without touching this path.
    """
    return PxlReaction(
        pxl = pixel,
        reaction_type = data[ 'type' ],
        reaction_color = data[ 'reaction_color' ],
        tolerance = data[ 'tolerance' ],
        reaction = data[ 'reaction' ],
        readiness = build_readiness( data ),
        confirm = data[ 'confirm' ],
        ignore_colors = data[ 'ignore_colors' ],
        name = name,
        trigger_log = trigger_log,
        cast_time = data[ 'cast_time' ],
        cast_lock = cast_lock,
    )


class TriggerLog:
    """
    Optional instrumentation that records the pixel color responsible for each reaction firing.

    Raw events are accumulated as exact-RGB counts per reaction (cheap, bounded by the number of
    distinct colors observed). `report()` then de-duplicates: it collapses near-identical colors
    (within `collapse_tolerance`, the same SSD metric as colors_different) into a single line and
    sums their counts. Because sustained-but-benign tints (poison, curse) fire far more often than
    genuine emergencies, their collapsed counts dominate the report - making them obvious candidates
    for a reaction's `ignore_colors`.

    When a `path` is configured the counts persist to a JSON file: prior data is loaded and merged
    at construction, the file is rewritten periodically during play (via `maybe_save`) and on exit,
    so the tally accumulates across sessions and the report is meaningful regardless of when it is
    consulted. The on-disk shape is { reaction_name: { "r,g,b": count } }.
    """

    def __init__( self, collapse_tolerance, verbose = False, path = None,
                  save_interval = 60.0 ):
        """
        Args:
            collapse_tolerance (int): SSD threshold below which two colors are merged in the report
                (typically the settings default color tolerance).
            verbose (bool): When True, echo a compact swatch line on every recorded trigger. Off by
                default to avoid scrolling the terminal during play.
            path (str | None): JSON file for persistence. None disables all disk I/O (in-memory only).
            save_interval (float): Minimum seconds between periodic `maybe_save` writes.
        """
        self.collapse_tolerance = collapse_tolerance
        self.verbose = verbose
        self.path = path
        self.save_interval = save_interval

        # reaction_name -> { rgb_tuple: count }
        self._counts = {}

        # Recording happens on the poll thread while periodic/exit saves may read concurrently; a
        # lock keeps the dict consistent during serialization.
        self._lock = threading.Lock()
        self._dirty = False
        self._last_save = time.perf_counter()

        if self.path:
            self.load()

    def record( self, reaction_name, rgb ):
        """Tally one trigger of `reaction_name` caused by color `rgb`."""
        if rgb is None:
            return
        with self._lock:
            bucket = self._counts.setdefault( reaction_name, {} )
            bucket[ rgb ] = bucket.get( rgb, 0 ) + 1
            self._dirty = True

        if self.verbose:
            print( f"  {describe_color( rgb )} -> {BLUE}{reaction_name}{RESET}" )

    def load( self ):
        """
        Merge counts from the JSON file into memory. Missing files are ignored; a corrupt or
        unreadable file is reported and skipped (the session starts a fresh tally rather than
        crashing). Color keys are stored as "r,g,b" strings and parsed back to int tuples.
        """
        if not self.path or not os.path.exists( self.path ):
            return
        try:
            with open( self.path, "r", encoding = "utf-8" ) as fh:
                data = json.load( fh )
        except ( OSError, ValueError ) as exc:
            print( f"{YELLOW}Trigger log: could not read {CYAN}{self.path}{RESET} ({exc}); starting fresh.{RESET}" )
            return

        with self._lock:
            for name, colors in data.items():
                bucket = self._counts.setdefault( name, {} )
                for key, count in colors.items():
                    try:
                        rgb = tuple( int( part ) for part in key.split( "," ) )
                    except ValueError:
                        continue
                    if len( rgb ) == 3:
                        bucket[ rgb ] = bucket.get( rgb, 0 ) + int( count )

    def save( self, force = False ):
        """
        Write the current counts to the JSON file. No-op when persistence is disabled or (unless
        `force`) nothing has changed since the last write. The write is atomic (temp file + replace)
        so a crash mid-write cannot corrupt long-lived data.
        """
        if not self.path:
            return
        with self._lock:
            if not force and not self._dirty:
                return
            payload = {
                name: { f"{r},{g},{b}": count for ( r, g, b ), count in colors.items() }
                for name, colors in self._counts.items()
            }
            self._dirty = False
            self._last_save = time.perf_counter()

        tmp = f"{self.path}.tmp"
        try:
            with open( tmp, "w", encoding = "utf-8" ) as fh:
                json.dump( payload, fh, indent = 2 )
            os.replace( tmp, self.path )
        except OSError as exc:
            print( f"{YELLOW}Trigger log: failed to write {CYAN}{self.path}{RESET} ({exc}).{RESET}" )

    def maybe_save( self ):
        """Save if at least `save_interval` seconds have elapsed since the last write. Cheap to poll."""
        if not self.path:
            return
        if ( time.perf_counter() - self._last_save ) >= self.save_interval:
            self.save()

    def _collapse( self, bucket ):
        """
        Greedily cluster a { rgb: count } bucket by `collapse_tolerance`. Colors are processed most-
        frequent first, so each cluster's representative is its highest-count color. Returns a list
        of [ representative_rgb, total_count, distinct_shades ].
        """
        clusters = []
        for rgb, count in sorted( bucket.items(), key = lambda kv: kv[ 1 ], reverse = True ):
            for cluster in clusters:
                if get_color_difference( rgb, cluster[ 0 ] ) <= self.collapse_tolerance:
                    cluster[ 1 ] += count
                    cluster[ 2 ] += 1
                    break
            else:
                clusters.append( [ rgb, count, 1 ] )
        return clusters

    def report( self ):
        """Print the collapsed trigger report, grouped by reaction and sorted by frequency."""
        with self._lock:
            snapshot = { name: dict( colors ) for name, colors in self._counts.items() }

        if not snapshot:
            print( f"{YELLOW}Trigger log empty - no reactions fired.{RESET}" )
            return

        print( f"\n{B_CYAN}=== Trigger Log Report ==={RESET}" )
        for name in sorted( snapshot ):
            clusters = self._collapse( snapshot[ name ] )
            total = sum( c[ 1 ] for c in clusters )
            print( f"{BLUE}[{name}]{RESET} {MAGENTA}{total}{RESET} triggers, "
                   f"{MAGENTA}{len( clusters )}{RESET} distinct color(s):" )
            for rep, count, shades in sorted( clusters, key = lambda c: c[ 1 ], reverse = True ):
                shade_note = f" {YELLOW}(+{shades - 1} near){RESET}" if shades > 1 else ""
                print( f"  {describe_color( rep )}  {MAGENTA}x{count}{RESET}{shade_note}" )


class PxlReactionRegistry:
    """
    Builds the runtime reaction registry from the profile configuration. Each profile reaction's
    declarative `press`/`glyph` pair is synthesized into the reaction callable (a PI.press plus the
    timing log line), replacing the react_XX methods of the inline-config era. Structural
    validation happens at load time in pxl_config.
    """

    def __init__( self, app ):
        self.app = app
        settings = app.settings

        # Optional trigger-color instrumentation; None when disabled so PxlReaction skips recording
        tlog = settings[ 'trigger_log' ]
        self.trigger_log = (
            TriggerLog(
                collapse_tolerance = tlog[ 'collapse_tolerance' ],
                verbose = tlog[ 'verbose' ],
                path = tlog[ 'path' ],
                save_interval = tlog[ 'save_interval' ],
            )
            if tlog[ 'enabled' ] else None
        )

        # Reaction construction goes through a factory so the hot path stays branch-free. Default is
        # the plain capture-free builder; capture debug mode swaps it once, here.
        self.reaction_factory = build_reaction
        self.snapshot = None
        capture = settings[ 'capture' ]
        if capture[ 'enabled' ]:
            try:
                from pxl_capture import SnapshotCapture, make_capturing_factory
            except ImportError as exc:
                print( f"{RED}capture mode needs the 'mss' package ({exc}); running without it.{RESET}" )
            else:
                self.snapshot = SnapshotCapture( capture[ 'dir' ] )
                self.reaction_factory = make_capturing_factory( self.snapshot,
                                                                capture[ 'width' ], capture[ 'height' ] )

        self.reactions_registry = {
            name: self._build_entry( name, data )
            for name, data in app.profile[ 'reactions' ].items()
        }

        self.clock = time.perf_counter
        self.last_reaction_ticks = { name: None for name in self.reactions_registry }

    def _build_entry( self, name, data ):
        """Translate a normalized profile reaction into a runtime registry entry."""
        return {
            'sx': data[ 'x' ],
            'sy': data[ 'y' ],
            'type': data[ 'type' ],
            'reaction_color': data[ 'color' ],
            'tolerance': data[ 'tolerance' ],
            'cooldown': data[ 'cooldown' ],
            'ready': data[ 'ready' ],
            'confirm': data[ 'confirm' ],
            'ignore_colors': data[ 'ignore_colors' ],
            'cast_time': data[ 'cast_time' ],
            'reaction': self._make_reaction( name, data[ 'press' ], data[ 'glyph' ] ),
        }

    def _make_reaction( self, name, press, glyph ):
        """Synthesize the reaction callable: send the configured key and log the firing."""
        def _react():
            self.app.PI.press( press )
            self._log_reaction( name, glyph )
        return _react

    def _log_reaction( self, key, glyph ):
        now_tick = self.clock()
        last_tick = self.last_reaction_ticks.get( key )
        delta_text = "--"

        if last_tick is not None:
            delta_seconds = now_tick - last_tick
            delta_text = f"{delta_seconds:.2f}s"

        self.last_reaction_ticks[ key ] = now_tick

        now_wall = time.strftime( "%H:%M:%S", time.localtime() )
        print( f"{glyph} {MAGENTA}{now_wall}{RESET} Δt {MAGENTA}{delta_text}{RESET}" )


if __name__ == "__main__":
    app = PxlReactApp()
    app.start_update_loop()

