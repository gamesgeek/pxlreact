"""
pxl_lib.py provides various utility functions for use throughout PxlReact; these may eventually find
a home in their own class.
"""

import colorsys
import ctypes
import threading
import time
from ctypes import wintypes
from ansi import *

# Allow for this much fluctuation in color before considering it "different enough"
COLOR_TOLERANCE = 4000

HDC = ctypes.windll.user32.GetDC( 0 )
WPT = wintypes.POINT()

# Several threads (winwatch, the main poll loop, the remapper) read pixels through the single
# shared screen DC. GDI is not safe for concurrent calls on one DC, so serialize access.
_HDC_LOCK = threading.Lock()
    

def _refresh_hdc():
    """
    Release and re-acquire the cached screen DC. Used to recover from an invalid read, which can
    happen if the DC has gone stale (display/mode change, DWM event). Call while holding _HDC_LOCK.
    """
    global HDC
    try:
        ctypes.windll.user32.ReleaseDC( 0, HDC )
    except Exception:
        pass
    HDC = ctypes.windll.user32.GetDC( 0 )

def get_active_window_rect():
    """
    Get the rectangle coordinates of the active window.
    
    Returns:
        tuple[int, int, int, int]: (left, top, right, bottom) coordinates of the active window,
                                  or None if no active window found.
    """
    try:
        # Get the handle to the active window
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if hwnd == 0:
            return None
            
        # Get window rectangle
        rect = wintypes.RECT()
        success = ctypes.windll.user32.GetWindowRect( hwnd, ctypes.byref( rect ) )
        if success == 0:
            return None
            
        return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        return None

def get_pixel_color( x, y ):
    """
    Retrieve the rgb values of the pixel at coordinates (x, y).

    Reads are serialized on _HDC_LOCK to avoid concurrent GDI access to the shared screen DC, which
    returns CLR_INVALID (-1) under contention. A single failed read is retried once after refreshing
    the DC; only a second failure is treated as a genuine bad read.
    """
    with _HDC_LOCK:
        pixel = ctypes.windll.gdi32.GetPixel( HDC, x, y )

        if pixel == -1:
            _refresh_hdc()
            pixel = ctypes.windll.gdi32.GetPixel( HDC, x, y )

            if pixel == -1:
                print( f'{MAGENTA}\tbad read at {YELLOW}{x}{RE}, {YELLOW}{y}{RE}' )
                return None

    red = pixel & 0xFF
    green = ( pixel >> 8 ) & 0xFF
    blue = ( pixel >> 16 ) & 0xFF
    return red, green, blue

def get_color_difference( c1, c2 ):
    """
    Calculate the sum of squared differences between two colors.
    """
    return sum( ( a - b ) ** 2 for a, b in zip( c1, c2 ) )

def colors_different( c1, c2 ):
    """
    True when the SSD of two colors exceeds tolerance (colors are "different enough")
    """
    delta = get_color_difference( c1, c2 )
    # if delta > COLOR_TOLERANCE:
    #     print( f"Color difference: {delta}" )
    return delta > COLOR_TOLERANCE

def colors_similar( c1, c2 ):
    """
    Return true if two colors are similar enough to be considered the same.
    """
    return not colors_different( c1, c2 )

class CastLock:
    """
    Shared "a cast is in progress" gate, coordinating the reaction system and the keyboard remapper.

    When armed for a duration, `active()` returns True until it elapses. The remapper drops injected
    remap presses while active so they cannot interrupt a cast; reactions (and remap actions with a
    cast_time) arm it when they fire. Thread-safe: armed from the reaction poll thread and read from
    the remapper thread. Arming never shortens an already-longer active cast.
    """

    def __init__( self ):
        self._until = 0.0
        self._lock = threading.Lock()

    def arm( self, duration ):
        with self._lock:
            self._until = max( self._until, time.perf_counter() + duration )

    def active( self ):
        with self._lock:
            return time.perf_counter() < self._until


def matches_any( color, palette ):
    """
    True when `color` is similar (within COLOR_TOLERANCE) to any color in `palette`.

    Used as a cheap allow-list test against an already-read pixel color; an empty or None palette
    yields False. Each comparison is a few integer ops, so testing a small palette every poll tick
    is negligible next to the GetPixel read that produced `color`.
    """
    if not palette:
        return False
    return any( colors_similar( color, ref ) for ref in palette )


class ColorCondition:
    """
    A single pixel-color condition: the pixel at (px, py) must either match `color` (match = True)
    or differ from it (match = False). `passes()` reads the pixel live and applies the test.

    Used to compose multi-layered checks where several conditions must all hold (logical AND).
    """

    __slots__ = ( 'px', 'py', 'color', 'match' )

    def __init__( self, px, py, color, match = True ):
        self.px = px
        self.py = py
        self.color = color
        self.match = match

    def passes( self ):
        """
        Read the configured pixel and return whether the condition holds. A failed read (None)
        fails the condition, since we cannot confirm the required state.
        """
        observed = get_pixel_color( self.px, self.py )
        if observed is None:
            return False
        if self.match:
            return colors_similar( observed, self.color )
        return colors_different( observed, self.color )

    def describe( self ):
        """Short '+'/'-' status glyph for terminal logging (matched expectation -> green '+')."""
        ok = self.passes()
        glyph = '+' if self.match else '!'
        return f"{GREEN}{glyph}{RESET}" if ok else f"{RED}{glyph}{RESET}"

def get_mouse_pos_window():
    """
    Get the current position of the mouse cursor in window-relative space.
    """
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if hwnd == 0:
        return None
    rect = wintypes.RECT()
    success = ctypes.windll.user32.GetWindowRect( hwnd, ctypes.byref( rect ) )
    if success == 0:
        return None

    ctypes.windll.user32.GetCursorPos( ctypes.byref( WPT ) )

    return WPT.x - rect.left, WPT.y - rect.top
    
def get_mouse_pos():
    """
    Get the current position of the mouse cursor.

    Returns:
        tuple[int, int]: The (x, y) screen coordinates of the mouse cursor.
    """
    ctypes.windll.user32.GetCursorPos( ctypes.byref( WPT ) )
    return WPT.x, WPT.y

def validate_color_at( x, y, color ):
    """
    Validate the color at the given coordinates (x, y) against the expected color.

    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate of the pixel.
        color (tuple[int, int, int]): The expected (R, G, B) color values.

    Returns:
        bool: True if the color matches, False otherwise.
    """
    pixel_color = get_pixel_color( x, y )
    if pixel_color is None:
        return False

    # validated = pixel_color == color
    # if not validated:
    #     print( pixel_color )

    return pixel_color == color

def rgb_to_hex( rgb ):
    """Convert an RGB tuple to a hexadecimal color."""
    return "#{:02x}{:02x}{:02x}".format( *rgb )

def color_name( rgb ):
    """
    Rough human hue label for an RGB color (e.g. "green", "purple"), to make the in-game association
    obvious in logs - a green tint reads as poison, a purple tint as a curse, etc. Low-saturation or
    very dark/light colors collapse to grey/black/white.
    """
    r, g, b = ( c / 255.0 for c in rgb )
    h, s, v = colorsys.rgb_to_hsv( r, g, b )

    if v < 0.12:
        return "black"
    if s < 0.12:
        return "white" if v > 0.75 else "grey"

    deg = h * 360.0
    for limit, name in ( ( 15, "red" ), ( 45, "orange" ), ( 70, "yellow" ), ( 170, "green" ),
                         ( 200, "cyan" ), ( 260, "blue" ), ( 320, "purple" ), ( 360, "red" ) ):
        if deg < limit:
            return name
    return "red"

def color_swatch( rgb, width = 2 ):
    """Return a small block colored with `rgb` as its terminal background (truecolor)."""
    r, g, b = rgb
    return f"{bg_rgb( r, g, b )}{' ' * width}{RESET}"

def describe_color( rgb ):
    """
    One-line visual + textual description of a color: a truecolor swatch, the hue name, the RGB
    triple, and the hex code. Used by reporting to make logged colors recognizable at a glance.
    """
    r, g, b = rgb
    return ( f"{color_swatch( rgb )} {color_name( rgb ):>6} "
             f"({MAGENTA}{r:>3}{RESET}, {MAGENTA}{g:>3}{RESET}, {MAGENTA}{b:>3}{RESET}) "
             f"{CYAN}{rgb_to_hex( rgb )}{RESET}" )

def find_most_similar_pixel( color, mnx, mny, mxx, mxy ):
    """
    Within the rectangle bounded by mnx, mny, mxx, mxy, find the color that is closest to the
    given color.
    """

    # The most similar color and its x,y coordinates
    msc = None
    msx = None
    msy = None

    smallest_difference = float('inf')

    # Search inclusively
    for x in range( min( mnx, mxx ), max( mnx, mxx ) + 1 ):
        for y in range( min( mny, mxy ), max( mny, mxy ) + 1 ):

            c = get_pixel_color( x, y )
            difference = get_color_difference( color, c )

            if difference < smallest_difference:
                smallest_difference = difference
                msc = c
                msx = x
                msy = y

    return msc, msx, msy, smallest_difference

def report_color_at( x, y, color = None ):
    """
    Print the RGB color value at the specified coordinates.

    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate of the pixel.
        color (tuple[int, int, int] | None): A pre-read color to report; if None, the pixel is read.

    Output format: (x, y) - (r, g, b) - 0xdddddd - #dddddd
    """
    if color is None:
        color = get_pixel_color( x, y )
    if color is None:
        print( f"{RED}Error: Could not read pixel at ({x}, {y}){RESET}" )
        return
    
    r, g, b = color
    hex_int = f"0x{r:02x}{g:02x}{b:02x}"
    hex_hash = f"#{r:02x}{g:02x}{b:02x}"
    
    print( f"({MAGENTA}{x}{RESET}, {MAGENTA}{y}{RESET}) - "
           f"({MAGENTA}{r}{RESET}, {MAGENTA}{g}{RESET}, {MAGENTA}{b}{RESET}) - "
           f"{MAGENTA}{hex_int}{RESET} - {MAGENTA}{hex_hash}{RESET}" )

def report_mouse_color( delay = 1 ):
    """
    Get the current mouse position, wait for the specified delay, then report the color at that position.
    
    Args:
        delay (float): The delay in seconds before reading the color (default: 1 second).
                      This allows the user to move the cursor away to avoid hover state interference.
    """
    x, y = get_mouse_pos()
    time.sleep( delay )
    report_color_at( x, y )


class PixelMonitor:
    """
    Toggleable background watcher for a single pixel, intended for screen discovery.

    On start it captures the current mouse position, waits an initial settle delay (so the cursor
    can be moved away and any hover state can clear), then polls that fixed coordinate and reports
    the color only when it changes - each distinct color is printed once, not on every poll.
    """

    def __init__( self, delay = 1.0, interval = 0.1 ):
        self.delay = delay
        self.interval = interval
        self._thread = None
        self._stop = threading.Event()
        self._x = None
        self._y = None
        self._last = None

    @property
    def active( self ):
        return self._thread is not None and self._thread.is_alive()

    def toggle( self ):
        """Start the monitor if stopped, otherwise stop it."""
        if self.active:
            self.stop()
        else:
            self.start()

    def start( self ):
        if self.active:
            return
        self._x, self._y = get_mouse_pos()
        self._last = None
        self._stop.clear()
        self._thread = threading.Thread( target = self._run, name = 'PixelMonitor', daemon = True )
        self._thread.start()
        print( f"👁️ {GREEN}pixel monitor on{RESET} ({MAGENTA}{self._x}{RESET}, {MAGENTA}{self._y}{RESET})" )

    def stop( self ):
        if not self.active:
            return
        self._stop.set()
        print( f"👁️ {YELLOW}pixel monitor off{RESET}" )

    def _run( self ):
        # Initial settle delay so the cursor can move away / hover states can clear
        if self._stop.wait( self.delay ):
            return
        while not self._stop.is_set():
            color = get_pixel_color( self._x, self._y )
            if color is not None and color != self._last:
                self._last = color
                report_color_at( self._x, self._y, color )
            self._stop.wait( self.interval )

