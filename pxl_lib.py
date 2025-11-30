"""
pxl_lib.py provides various utility functions for use throughout PxlReact; these may eventually find
a home in their own class.
"""

import ctypes
import time
from ctypes import wintypes
from ansi import *


# Certain common in-game events can trigger false-positives and reactions; examples include flashing lights,
# electric shock, temporary dialogs, etc. This list lets us ignore these and avoid extra reactions.

# Allow for this much fluctuation in color before considering it "different enough"
COLOR_TOLERANCE = 400


HDC = ctypes.windll.user32.GetDC( 0 )
WPT = wintypes.POINT()

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
    Retrieve the rgb values of the pixel at coordinates (x, y)
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
    Calculate the sum of squared differences between two colors.
    """
    return sum( ( a - b ) ** 2 for a, b in zip( c1, c2 ) )

def colors_different( c1, c2 ):
    """
    True when the SSD of two colors exceeds tolerance (colors are "different enough")
    """
    delta = get_color_difference( c1, c2 )
    return delta > COLOR_TOLERANCE

def colors_similar( c1, c2 ):
    """
    Return true if two colors are similar enough to be considered the same.
    """
    return not colors_different( c1, c2 )

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

def report_color_at( x, y ):
    """
    Print the RGB color value at the specified coordinates.
    
    Args:
        x (int): The x-coordinate of the pixel.
        y (int): The y-coordinate of the pixel.
    
    Output format: (x, y) - (r, g, b) - 0xdddddd - #dddddd
    """
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


