import json
import ctypes
from ctypes import wintypes
from ansi import *
import math
import pyautogui
import time

DEBUGGING = False

# A bit of a "hack" to ignore common events that can alter the color of certain key pixels in ways
# that we do not actually want to respond to; e.g., flashing lights, electric shock, etc.
IGNORED_DELTAS = [ 17325, 24626, 16490, 62774, 63134, 35762 ]

# Allow for this much fluctuation in color before considering it "different enough"
COLOR_TOLERANCE = 8600


def draw_mouse_indicator( x, y ):
    """
    Draws a small 2x2 pixel magenta square at the given screen position.
    """
    try:
        pyautogui.screenshot( region = ( x, y, 2, 2 ) ).save( "temp_mouse_indicator.png" )
        pyautogui.pixel( x, y ) # Access the pixel to ensure it's reachable
        pyautogui.moveTo( x, y ) # Move to position (optional, just to ensure focus)
        pyautogui.click( x, y, _pause = False ) # Click to refresh (optional)
    except Exception as e:
        print( f"Could not draw mouse indicator: {e}" )


def get_pixel_color( x, y ):
    """
    Retrieve the color value of the pixel at coordinates (x, y) or under the mouse if called without arguments.

    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate

    Returns:
        tuple[int, int, int]: The (R, G, B) color values of the pixel.
    """
    pixel = ctypes.windll.gdi32.GetPixel( HDC, x, y )
    if pixel == -1:
        return None

    red = pixel & 0xFF
    green = ( pixel >> 8 ) & 0xFF
    blue = ( pixel >> 16 ) & 0xFF
    return red, green, blue


def get_color_difference( c1, c2 ):
    """
    Returns the sum of squared differences (SSD) between the two colors.
    Larger differences are weighted more heavily.
    """
    return sum( ( a - b ) ** 2 for a, b in zip( c1, c2 ) )


def colors_different( c1, c2 ):
    """
    Return true if two colors are too different to be considered the same.
    Print a warning if they’re over tolerance, or nearly so.
    """
    delta = get_color_difference( c1, c2 )
    if delta in IGNORED_DELTAS:
        return False
    # how close to tolerance counts as “nearly”
    # NEAR_RATIO = 0.85

    # if delta > COLOR_TOLERANCE:
    #     print( f"  Color difference: {YELLOW}{delta}{RE} "
    #            f"(c1: {MAGENTA}{c1}{RE}, c2: {RED}{c2}{RE})" )
    # elif delta > COLOR_TOLERANCE * NEAR_RATIO:
    #     print( f"  Nearly different: {YELLOW}{delta}{RE} "
    #            f"(c1: {MAGENTA}{c1}{RE}, c2: {RED}{c2}{RE})" )

    return delta > COLOR_TOLERANCE


def colors_similar( c1, c2 ):
    """
    Return true if two colors are similar enough to be considered the same.
    """
    return not colors_different( c1, c2 )


def debug_func( func_name, *args ):
    """
    Print a nicely-formatted representation of a function call & its arguments for debugging purposes.
    """
    if not DEBUGGING:
        return

    string_color = YELLOW
    num_color = RED
    bool_color = MAGENTA
    container_color = CYAN
    none_color = B_BLACK
    param_parts = []

    # Construct the output string by appending the arguments, highlighting each according to type
    for arg in args:
        if arg is None:
            color = none_color
        if isinstance( arg, str ):
            color = string_color
        elif isinstance( arg, ( int, float ) ):
            color = num_color
        elif isinstance( arg, bool ):
            color = bool_color
        elif isinstance( arg, ( list, tuple, set, dict ) ):
            color = container_color

        param_parts.append( f"{color}{repr(arg)}{RE}" )

    lp = f'{WHITE}( {RE}'
    rp = f'{WHITE} ){RE}'
    func_str = f'{GREEN}{func_name}{RE}'
    param_str = ", ".join( param_parts )
    print( f"{func_str}{lp}{param_str}{rp}" )


def rgb_to_hex( rgb ):
    """Convert an RGB tuple to a hexadecimal color."""
    return "#{:02x}{:02x}{:02x}".format( *rgb )


HDC = ctypes.windll.user32.GetDC( 0 )
WPT = wintypes.POINT()


def get_mouse_pos():
    """
    Get the current position of the mouse cursor.

    Returns:
        tuple[int, int]: The (x, y) screen coordinates of the mouse cursor.
    """
    ctypes.windll.user32.GetCursorPos( ctypes.byref( WPT ) )
    return WPT.x, WPT.y


def circle_points():
    """
    Generate points around a circle in a counter-clockwise order starting from the current mouse position and
    centered on the screen's center pixel.
    """

    num_points = 720

    # Starting at the current mouse position
    x0, y0 = get_mouse_pos()

    # Draw a counter-clockwise circle around the center of the screen
    cx, cy = 1280, 720

    # Radius is the distance from center to the known point on the circle
    r = math.hypot( x0 - cx, y0 - cy )

    # Starting angle
    start_angle = math.atan2( y0 - cy, x0 - cx )

    # We do a full revolution from start_angle down to (start_angle - 2π)
    # in small increments. Subtracting 2π ensures a CCW path when
    # y-axis is oriented "up" as in standard math (not screen coordinates).
    points = []
    for i in range( num_points ):
        # fraction of the way around the circle
        t = i / ( num_points - 1 ) # goes from 0 to 1
        # current angle (subtract 2π to move CCW in standard math orientation)
        theta = start_angle - 2.0 * math.pi * t
        x = cx + r * math.cos( theta )
        y = cy + r * math.sin( theta )
        points.append( ( x, y ) )

    return points


def write_json( data, filepath ):
    """
    Write dict to JSON
    """
    try:
        with open( filepath, 'w' ) as file:
            json.dump( data, file, indent = 2 )

    except Exception as e:
        print( f"Error writing JSON: {e}" )


def read_json( filepath, mode = 'r' ):
    """
    Read JSON to dict
    """
    try:
        with open( filepath, mode ) as file:
            rawdata = json.load( file )
            return rawdata

    except Exception as e:
        print( f"Error loading JSON file: {e}" )
        return None


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

    return pixel_color == color
