"""
PxlWinCheck is a single-purpose class designed to answer, on demand, whether the project should be acting: the correct application is in the foreground and a marker pixel is the expected color.

Unlike the former polling design, this performs no background work and holds no cached flag; each call to check() reads the live window title and marker pixel so the result reflects the screen at the instant of the call (e.g. a key press or pixel reaction), avoiding stale-flag false triggers during state transitions such as loading screens.
"""

import win32gui
from pxl_lib import validate_color_at
from ansi import *


class PxlWinCheck:

    def __init__( self ):

        # The application we're monitoring; must be the active window
        self.target_app = 'Path of Exile 2'

        """
        The location and color of a key "indicator pixel" that shows us we're in the right state for pxlreact to operate; this is a precise check (validate_color_at) deliberately, as protecting against inadvertant reactions is key.
        """
        #(22, 1074) - (169, 167, 144)
        self.marker_x = 22
        self.marker_y = 1074
        self.marker_color = ( 169, 167, 144 )

    def marker_ok( self ):
        return validate_color_at( self.marker_x, self.marker_y, self.marker_color )

    def in_target_app( self ):
        return self.target_app == win32gui.GetWindowText( win32gui.GetForegroundWindow() )

    def check( self ):
        return self.in_target_app() and self.marker_ok()

    def check_slow( self ):
        """
        Debug version of check that will tell us why the app is inactive; use if this stops working,
        which sometimes happens after updates or with overlay apps that make subtle color changes.
        """
        in_app = self.in_target_app()
        marker_ok = self.marker_ok()
        if not in_app or not marker_ok:
            print( f"PxlWinCheck: app: {in_app} marker: {marker_ok}" )
        return in_app and marker_ok
