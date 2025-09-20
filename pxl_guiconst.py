"""
pxl_guiconst.py includes a wide range of constants for use in defining the size and position of GUI elements; many of
these are currently unused but are included here for additional context and in case they come in handy in the future.

Abbreviations in use throughout the constant names:
    - W = Width
    - H = Height
    - L = Left boundary
    - R = Right boundary
    - CX = Center x-coordinate
    - CY = Center y-coordinate
    - WIN = "Window" or the pxlreact application GUI
    - PX = Abbreviation for pixel and also used for variables related to the "pixel areas"
    - T = Top
    - B = Bottom
    - H = Horizontal if it's not Height
    - V = Vertical
"""

# Screen/Display Dimensions
SCREEN_W = 2560
SCREEN_H = 1440

# Space between pxlreact and the edge of the physical display
SCREEN_PAD = 33

# Either from Windows or tkinter, the PxlReact window maintains a 2-pixel wide frame which counts as part of the canvas
# but cannot be used for drawing; so we account for it in our sizing and positioning calculations.
WIN_FRAME = 2

# Padding to leave between and around GUI components
PAD = 4

# Font spacing and current line count to help make enough space for pixel data text
FONT = "Consolas"
TEXT_SIZE = 12
TEXT_LINESPACE = 1.2
TEXT_LINES = 3

BIG_PXL_DIM = 32

# Colors for various elements
TEXT_COLOR = '#DADB74'
BIG_PXL_FRAME = '#DADB74'
LINE_COLOR = '#2B3856'
BG_COLOR = '#000000'

# Position GUI in the bottom-right of the left-hand monitor (we will usually be using pxlreact to monitor an application
# on the right-hand monitor.
WIN_W = 401
WIN_H = 281

# The "outer bounds" of the GUI window; therefore these values are set relative to the screen rather than the GUI
WIN_T = SCREEN_H - ( WIN_H + SCREEN_PAD )
WIN_L = -( WIN_W + SCREEN_PAD )
# Temporarily move window to right-monitor, bottom-left
# WIN_L = SCREEN_PAD
WIN_B = WIN_T + WIN_H
WIN_R = WIN_L + WIN_W

# tkinter's "canvas" is inclusive of the pixels reserved for the window border; so we define our own canvas with "real"
# borders that are within the useable space of the GUI window; validated a single-pixel width rectangle drawn to these
# corners perfectly surrounds the drawable area of the window
DRAWABLE_W = WIN_W - ( 2 * WIN_FRAME )
DRAWABLE_H = WIN_H - ( 2 * WIN_FRAME )
DRAWABLE_L = WIN_FRAME
DRAWABLE_T = WIN_FRAME
DRAWABLE_R = WIN_W - WIN_FRAME
DRAWABLE_B = WIN_H - WIN_FRAME
DRAWABLE_CX = DRAWABLE_L + ( DRAWABLE_R - DRAWABLE_L ) // 2
DRAWABLE_CY = DRAWABLE_T + ( DRAWABLE_B - DRAWABLE_T ) // 2

# Vertitcal & Horizontal count of the grid of "pixel areas" to display in the GUI; recall "row 0" is reserved for the
# "mouse preview" area which will have identical dimensions to a row of areas.
# MOUSE_PREVIEW_ROWS is included here simply to illustrate that it must be accounted for in addition to the grid; the
# topmost row will always be reserved for a "MOUSE_PREVIEW" area having the same dimensions as all other areas but existing
# on its own row.
MOUSE_PREVIEW_ROWS = 1
PX_GRID_ROWS = 2 + MOUSE_PREVIEW_ROWS
PX_GRID_COLS = 2

# Account for the (n - 1) spacing gaps we will have vertically and horizontally
PX_GRID_VPAD = ( PX_GRID_ROWS - 1 ) * PAD
PX_GRID_HPAD = ( PX_GRID_COLS - 1 ) * PAD

# Dimensions, borders, and "dead center" for pixel display area grid
PX_GRID_W = DRAWABLE_W - ( 2 * PAD )
PX_GRID_H = DRAWABLE_H - ( 2 * PAD )
PX_GRID_L = DRAWABLE_L + PAD
PX_GRID_R = DRAWABLE_R - PAD
PX_GRID_T = DRAWABLE_T + PAD
PX_GRID_B = DRAWABLE_B - PAD
PX_GRID_CX = PX_GRID_L + ( PX_GRID_R - PX_GRID_L ) // 2
PX_GRID_CY = PX_GRID_T + ( PX_GRID_B - PX_GRID_T ) // 2

PX_GRID = {}
BIG_PX_GRID = {}

PX_CELL_W = ( PX_GRID_W - PX_GRID_HPAD ) // PX_GRID_COLS
PX_CELL_H = ( PX_GRID_H - PX_GRID_VPAD ) // PX_GRID_ROWS

TOTAL_HPAD = PX_GRID_HPAD + ( 2 * PAD )
TOTAL_VPAD = PX_GRID_VPAD + ( 2 * PAD )

# Using the font size and intended lines of data text plus line spacing estimate (1.2), try and roughly guess how
# much vertical space to allow for the pixel data text; every pixel area must be at least this tall
TEXT_HEIGHT = round( TEXT_LINES * ( TEXT_SIZE * TEXT_LINESPACE ) )

# Geometry string for the GUI window
WIN_POS = f'{WIN_W}x{WIN_H}+{WIN_L}+{WIN_T}'
