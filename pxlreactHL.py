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

from pxl_remap_maps import ACTIONS, ROTATIONS, REMAPS

class PxlReactApp:
    """
    PxlReactApp is the main application class for the PxlReact project; it initializes the GUI and manages the list of
    pixels being monitored (formerly PxlWatcher).
    """

    def __init__( self ):
        """
        Args:
            pixel_count (int): Maximum number of pixels we will monitor
            tick_interval (float): How often (in seconds) to poll for pixel color changes; longer
                intervals may miss rapid changes
        """

        # On-demand window/marker gate; check() is evaluated live at each reaction/remap fire point
        self.wincheck = PxlWinCheck()

        self.PI = PxlIntercept()

        self.stop_event = threading.Event()

        # Shared cast lock: a cast-time reaction arms it so the remapper drops keypresses that would
        # otherwise interrupt the cast; remap actions with a cast_time arm the same lock.
        self.cast_lock = CastLock()

        # Keyboard-capture remapping layer (starts its own background thread); also owns the
        # F12/ESC quit and Ctrl+P report-color command hotkeys
        self.remapper = PxlRemapper( self.wincheck, ACTIONS, ROTATIONS, REMAPS,
                                     on_quit = self.exit_application, cast_lock = self.cast_lock )

        self.pixel_count = 3
        self.tick_interval = 0.025

        # Initialize the list; index 0 is unused in lite (no mouse preview)
        self.pixels = [ None ] * ( self.pixel_count + 1 )

        # Add regular pixels starting at index 1; assign arbitrary initial pixel coordinates and
        # pass a reference to ourselves so Pxl's can remember us
        for i in range( 1, self.pixel_count + 1 ):
            self.pixels[ i ] = Pxl( i, i * 11, i * 11, app = self )

        self.registry = PxlReactionRegistry( self )

        # self.load_reaction( 1, "HP1" )
        self.load_reaction( 1, "MP1" )
        self.load_reaction( 2, "CV1" )

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
                for pxl in self.pixels[ 1: ]:
                    if pxl is None:
                        continue
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

    def reassign_pixel( self, index, x = None, y = None ):
        """
        For simplicity; pixels are pre-assigned a default position at load, so all assignments are really re-assignments;
        x, y are set based on the mouse position, but can be supplied directly to facilitate loading configurations from
        file.
        """

        pxl = self.pixels[ index ]

        if x is None or y is None:
            x, y = get_mouse_pos()

        pxl.sx = x
        pxl.sy = y

        pxl.update_color()

    def load_reaction( self, pixel_index, reaction_name ):
        """
        Load a reaction from the registry and assign it to a specific pixel,
        including reassigning the pixel to the coordinates from the registry.

        Args:
            pixel_index (int): The index of the pixel to assign the reaction.
            reaction_name (str): The name of the reaction in the registry.
        """

        # Get the reaction definition
        reaction_data = self.registry.reactions_registry.get( reaction_name )

        if not reaction_data:
            raise ValueError( f"Reaction '{reaction_name}' not found in registry" )

        # Reassign the pixel to monitor the sx, sy coordinates from the reaction definition
        self.reassign_pixel( pixel_index, x = reaction_data[ 'sx' ], y = reaction_data[ 'sy' ] )

        # Build the reaction via the registry's factory (plain by default; capture mode swaps the
        # factory once at startup, so this construction site needs no capture branching).
        pixel = self.pixels[ pixel_index ]
        pixel.set_reaction(
            self.registry.reaction_factory( pixel, reaction_data, reaction_name,
                                            self.registry.trigger_log, self.cast_lock )
        )
        rx = reaction_data['sx']
        ry = reaction_data['sy']
        print( f"[{pixel_index}] {BLUE}{reaction_name}{RESET} @ ({rx}, {ry})" )

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
    (e.g. a skill icon) shows the expected color. Suited to emergency abilities whose cooldown is
    too variable to time, but which expose an on-screen ready/not-ready indicator.

    A short `lockout` after firing suppresses immediate re-triggering during the brief window before
    the indicator updates to its not-ready color (otherwise the poll loop could fire several times).
    """

    def __init__( self, px, py, color, lockout = 0.5 ):
        self.px = px
        self.py = py
        self.color = color
        self.lockout = lockout
        self._last = -1.0

    def ready( self ):
        if self._last >= 0 and ( time.perf_counter() - self._last ) < self.lockout:
            return False
        observed = get_pixel_color( self.px, self.py )
        return observed is not None and colors_similar( observed, self.color )

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

    def __init__( self, pxl, reaction_type, reaction_color, reaction, readiness, confirm = 0.0,
                  ignore_colors = None, name = None, trigger_log = None, cast_time = 0.0,
                  cast_lock = None ):
        """
        Initialize a PxlReaction instance.

        Args:
            pixel_index (int): The index of our "parent" Pxl (i.e., the one that determines if we trigger)
            reaction_type (str): Type of reaction; "react_if_not_color" fires when the pixel deviates
                from `reaction_color`, "react_if_color" fires when it matches `reaction_color`.
            reaction_color (tuple[int, int, int]): Target RGB color for the reaction.
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
            return colors_similar( rgb, self.reaction_color )
        # default: react_if_not_color
        return colors_different( rgb, self.reaction_color ) and not matches_any( rgb, self.ignore_colors )

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


def _build_one_readiness( spec, data ):
    """Build a single readiness strategy from one `ready` spec dict."""
    rtype = spec.get( 'type', 'cooldown' )
    if rtype == 'color':
        return ColorReadiness( spec[ 'px' ], spec[ 'py' ], spec[ 'color' ], spec.get( 'lockout', 0.5 ) )
    if rtype == 'cooldown':
        return CooldownReadiness( spec.get( 'cooldown', data.get( 'cooldown', 0.5 ) ) )
    raise ValueError( f"Unknown readiness type: {rtype}" )


def build_readiness( data ):
    """
    Construct a reaction's readiness strategy from its registry entry.

    `ready` may be a single spec dict, or a LIST of spec dicts that must ALL be ready (AND, via
    CompositeReadiness). Each spec is { 'type': 'color', 'px', 'py', 'color', 'lockout'? } for
    pixel-color readiness, or { 'type': 'cooldown', 'cooldown' } for time readiness. When `ready` is
    absent the `cooldown` shorthand is used (time readiness).
    """
    spec = data.get( 'ready' )
    if spec is None:
        return CooldownReadiness( data.get( 'cooldown', 0.5 ) )
    if isinstance( spec, ( list, tuple ) ):
        return CompositeReadiness( [ _build_one_readiness( s, data ) for s in spec ] )
    return _build_one_readiness( spec, data )


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
        reaction = data[ 'reaction' ],
        readiness = build_readiness( data ),
        confirm = data.get( 'confirm', 0.0 ),
        ignore_colors = data.get( 'ignore_colors' ),
        name = name,
        trigger_log = trigger_log,
        cast_time = data.get( 'cast_time', 0.0 ),
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

    def __init__( self, collapse_tolerance = COLOR_TOLERANCE, verbose = False, path = None,
                  save_interval = 60.0 ):
        """
        Args:
            collapse_tolerance (int): SSD threshold below which two colors are merged in the report.
                Defaults to COLOR_TOLERANCE (the same "similar enough" threshold reactions use).
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

    reaction_types = [ "react_if_color", "react_if_not_color" ]

    # (166, 1235) - (136, 192, 204
    cv_reaction_color = (136, 192, 204)

    # Benign off-colors at the CV pixel that must NOT trigger (e.g. curse tints); same role as
    # hp_ignore_colors but for the CV1 reaction.
    cv_ignore_colors = [
        (186, 140, 207),
    ]

    # CV1 readiness: fire only when BOTH a 6 s minimum cooldown has elapsed AND the skill's icon
    # shows it is available (the cooldown is variable, so the color guards true availability while
    # the 6 s floor prevents rapid re-triggering).
    # (2153, 1384) - (71, 204, 237)
    cv_ready_check = [
        { 'type': 'cooldown', 'cooldown': 6 },
        { 'type': 'color', 'px': 2153, 'py': 1384, 'color': (71, 204, 237) },
    ]

    # HP is now Energy Shield for my Build
    # (83, 1223) - (74, 114, 126)
    hp_reaction_color = (74, 114, 126)

    # Benign off-colors at the HP/ES pixel that must NOT trigger a reaction: sustained status-effect
    # tints (poison, curse, etc.) shift the orb color without indicating real depletion. Populate by
    # reading the tinted orb with the Ctrl+P pixel monitor and adding each RGB here. Empty until
    # measured; an empty list disables the ignore filter.
    hp_ignore_colors = []

    # (2418, 1357) - (14, 47, 100)
    mp_reaction_color = (14, 47, 100)

    # How long our flasks take to recharge (don't try to use them more often than this)
    hp_cooldown = 5
    mp_cooldown = 3

    # Seconds an off-color reading must persist before a reaction fires. Filters brief status-effect
    # tints (shocked/poisoned, etc.) that change tghe pixel for only a few frames. Raise if transient
    # effects still leak through; lower if real reactions feel sluggish.
    confirm_window = 0.1

    # Trigger-log instrumentation: when enabled, every reaction firing records the color that caused
    # it, and a collapsed frequency report is printed at exit. Use the report to discover which
    # colors fire reactions most often (poison/curse tints dominate) and add them to ignore_colors.
    trigger_log_enabled = True
    # Echo a swatch line on every trigger (noisy); leave False to only see the exit report.
    trigger_log_verbose = False
    # SSD threshold for merging near-identical colors in the report (defaults to COLOR_TOLERANCE).
    trigger_log_collapse_tolerance = COLOR_TOLERANCE
    # JSON file the trigger tally persists to (accumulates across sessions); None disables disk I/O.
    trigger_log_path = "trigger_log.json"
    # Seconds between periodic saves during play; the file is also written on exit.
    trigger_log_save_interval = 60.0

    # --- Capture debug mode (optional; requires pxl_capture.py + `pip install mss`) ---------------
    # When enabled, each reaction saves a PNG of a screen region centered on its pixel, captured
    # just BEFORE the key is sent, so misfires can be verified by eye. Off by default and fully
    # isolated: turning it off restores the plain capture-free path with no runtime branching, and
    # deleting pxl_capture.py + the capture block in __init__ removes it entirely.
    capture_enabled = False
    capture_dir = "captures"
    capture_w = 400
    capture_h = 300

    def __init__( self, app ):
        """
        Class to hold a registry of predefined reactions that can be assigned to pixels.
        """

        # Safeguard against random typos that have gotten me killed before...
        # if self.hp_cooldown > 5 or self.mp_cooldown > 5:
        #     raise ValueError( f"Flask cooldowns: {self.hp_cooldown}/{self.mp_cooldown}" )

        self.app = app

        # Optional trigger-color instrumentation; None when disabled so PxlReaction skips recording
        self.trigger_log = (
            TriggerLog(
                collapse_tolerance = self.trigger_log_collapse_tolerance,
                verbose = self.trigger_log_verbose,
                path = self.trigger_log_path,
                save_interval = self.trigger_log_save_interval,
            )
            if self.trigger_log_enabled else None
        )

        # Reaction construction goes through a factory so the hot path stays branch-free. Default is
        # the plain capture-free builder; capture debug mode swaps it once, here.
        self.reaction_factory = build_reaction
        self.snapshot = None
        if self.capture_enabled:
            try:
                from pxl_capture import SnapshotCapture, make_capturing_factory
            except ImportError as exc:
                print( f"{RED}capture mode needs the 'mss' package ({exc}); running without it.{RESET}" )
            else:
                self.snapshot = SnapshotCapture( self.capture_dir )
                self.reaction_factory = make_capturing_factory( self.snapshot, self.capture_w, self.capture_h )

        self.reactions_registry = {
            'HP1': {
                'sx': 83,
                'sy': 1223,
                'type': 'react_if_not_color',
                'reaction_color': self.hp_reaction_color,
                'cooldown': self.hp_cooldown,
                'confirm': self.confirm_window,
                'ignore_colors': self.hp_ignore_colors,
                'reaction': self.react_HP
            },
            'MP1': {
                'sx': 2418,
                'sy': 1357,
                'type': 'react_if_not_color',
                'reaction_color': self.mp_reaction_color,
                'cooldown': self.mp_cooldown,
                'confirm': self.confirm_window,
                'reaction': self.react_MP
            },
            'CV1': {
                'sx': 166,
                'sy': 1235,
                'type': 'react_if_not_color',
                'reaction_color': self.cv_reaction_color,
                'ready': self.cv_ready_check,
                'confirm': self.confirm_window,
                'ignore_colors': self.cv_ignore_colors,
                'cast_time': 0.4,
                'reaction': self.react_CV
            }
        }

        self.clock = time.perf_counter
        
        self.last_reaction_ticks = {
            'HP1': None,
            'MP1': None,
            'CV1': None,
        }

        self.validate_registry()

    def react_HP( self ):
        self.app.PI.press( "F" )
        self._log_reaction( 'HP1', "+❤️+" )

    def react_MP( self ):
        self.app.PI.press( "2" )
        self._log_reaction( 'MP1', "*✨*" )

    def react_CV( self ):
        self.app.PI.press( "T" )
        self._log_reaction( 'CV1', "~🧿~" )

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

    def validate_registry( self ):
        """
        Do a validation pass at load time to try and ensure there are no invalid entries in the reaction registry.

        Validate the reactions_registry ensuring every entry has:
            - sx >= -2560 and sx < 2560
            - sy >= 0 and sy < 1440
            - type as one of reaction_types
            - valid reaction_color as rgb tuple (0-255)
            - cooldown values that are not unreasonably high
            - reaction refers to a valid function
        """
        for name, reaction in self.reactions_registry.items():
            # Validate `sx` and `sy` coordinates
            if not ( -2560 <= reaction.get( 'sx', 0 ) < 2560 ):
                raise ValueError( f"Invalid 'sx' for reaction '{name}': {reaction['sx']}" )
            if not ( 0 <= reaction.get( 'sy', 0 ) < 1440 ):
                raise ValueError( f"Invalid 'sy' for reaction '{name}': {reaction['sy']}" )

            # Validate reaction type
            if reaction.get( 'type' ) not in self.reaction_types:
                raise ValueError( f"Invalid 'type' for reaction '{name}': {reaction['type']}" )

            # Validate `reaction_color`
            color = reaction.get( 'reaction_color' )
            if not ( isinstance( color, tuple ) and len( color ) == 3 and all( 0 <= c <= 255 for c in color ) ):
                raise ValueError( f"Invalid 'reaction_color' for reaction '{name}': {color}" )

            # Validate readiness: an explicit `ready` spec (a single dict or a list of dicts, each
            # color or cooldown) or the `cooldown` shorthand (time readiness).
            ready = reaction.get( 'ready' )
            if ready is not None:
                specs = ready if isinstance( ready, ( list, tuple ) ) else [ ready ]
                for spec in specs:
                    rtype = spec.get( 'type', 'cooldown' )
                    if rtype == 'color':
                        if not ( -2560 <= spec.get( 'px', 0 ) < 2560 ) or not ( 0 <= spec.get( 'py', 0 ) < 1440 ):
                            raise ValueError( f"Invalid 'ready' pixel for reaction '{name}': {spec}" )
                        rcolor = spec.get( 'color' )
                        if not ( isinstance( rcolor, tuple ) and len( rcolor ) == 3 and all( 0 <= c <= 255 for c in rcolor ) ):
                            raise ValueError( f"Invalid 'ready' color for reaction '{name}': {rcolor}" )
                        lockout = spec.get( 'lockout', 0 )
                        if not ( 0 <= lockout < 10 ):
                            raise ValueError( f"Unreasonable 'ready' lockout for reaction '{name}': {lockout}" )
                    elif rtype == 'cooldown':
                        cd = spec.get( 'cooldown', 0 )
                        if not ( 0 < cd < 180 ):
                            raise ValueError( f"Unreasonable 'ready' cooldown for reaction '{name}': {cd}" )
                    else:
                        raise ValueError( f"Unknown 'ready' type for reaction '{name}': {rtype}" )
            else:
                cooldown = reaction.get( 'cooldown', 0 )
                if not ( 0 < cooldown < 180 ): # avoid ms/s confusion with cooldowns (never > 3 minutes)
                    raise ValueError( f"Unreasonable 'cooldown' for reaction '{name}': {cooldown}" )

            # Validate `confirm` (debounce window); 0 disables debounce, cap well under a cooldown
            confirm = reaction.get( 'confirm', 0 )
            if not ( 0 <= confirm < 2 ):
                raise ValueError( f"Unreasonable 'confirm' for reaction '{name}': {confirm}" )

            # Validate optional `cast_time`; 0 disables cast protection, cap at a sane ceiling
            cast_time = reaction.get( 'cast_time', 0 )
            if not ( 0 <= cast_time < 10 ):
                raise ValueError( f"Unreasonable 'cast_time' for reaction '{name}': {cast_time}" )

            # Validate optional `ignore_colors` (benign off-colors); must be a list of RGB tuples
            ignore_colors = reaction.get( 'ignore_colors' )
            if ignore_colors is not None:
                if not isinstance( ignore_colors, ( list, tuple ) ):
                    raise ValueError( f"Invalid 'ignore_colors' for reaction '{name}': must be a list" )
                for ic in ignore_colors:
                    if not ( isinstance( ic, tuple ) and len( ic ) == 3 and all( 0 <= c <= 255 for c in ic ) ):
                        raise ValueError( f"Invalid entry in 'ignore_colors' for reaction '{name}': {ic}" )

            # Validate `reaction` as a callable
            if not callable( reaction.get( 'reaction' ) ):
                raise ValueError( f"Invalid 'reaction' for reaction '{name}': Must be a callable." )


if __name__ == "__main__":
    app = PxlReactApp()
    app.start_update_loop()

