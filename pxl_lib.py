"""
pxl_lib.py provides various utility functions for use throughout PxlReact; these may eventually find
a home in their own class.
"""
import ctypes
from ctypes import wintypes
from ansi import *

DEBUGGING = False

# Certain common in-game events can trigger false-positives and reactions; examples include flashing lights,
# electric shock, temporary dialogs, etc. This list lets us ignore these and avoid extra reactions.
IGNORED_DELTAS = [ 17325, 24626, 16490, 62774, 63134, 35762, 18518, 26521 ]


HDC = ctypes.windll.user32.GetDC( 0 )
WPT = wintypes.POINT()


def get_pixel_color( x, y ):
    """
    Retrieve the rgb values of the pixel at coordinates (x, y)
    """
    pixel = ctypes.windll.gdi32.GetPixel( HDC, x, y )
    if pixel == -1:
        return None

    red = pixel & 0xFF
    green = ( pixel >> 8 ) & 0xFF
    blue = ( pixel >> 16 ) & 0xFF
    return red, green, blue

# Allow for this much fluctuation in color before considering it "different enough"
COLOR_TOLERANCE = 8000

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
    return delta not in IGNORED_DELTAS and delta > COLOR_TOLERANCE



def colors_different( c1, c2 ):
    """
    Return true if two colors are "too different" to be considered the same.
    """
    delta = get_color_difference( c1, c2 )
    different = delta not in IGNORED_DELTAS and delta > COLOR_TOLERANCE
    # If different, print a highlighted message showing the delta (in case we want to add it to IGNORE) 
    if different:
        print( f"{YELLOW}{delta}{RE} (c1: {MAGENTA}{c1}{RE}, c2: {RED}{c2}{RE})" )
    return different


def colors_similar( c1, c2 ):
    """
    Return true if two colors are similar enough to be considered the same.
    """
    return not colors_different( c1, c2 )


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

    return pixel_color == color


def rgb_to_hex( rgb ):
    """Convert an RGB tuple to a hexadecimal color."""
    return "#{:02x}{:02x}{:02x}".format( *rgb )

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

