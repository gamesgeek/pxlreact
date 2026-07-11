"""
PxlWinCheck is a single-purpose class designed to answer, on demand, whether the project should be
acting: the correct application is in the foreground and every marker pixel is its expected color.

This performs no background work and holds no cached flag; each call to check() reads the live
window title and marker pixels so the result reflects the screen at the instant of the call (e.g. a
key press or pixel reaction), avoiding stale-flag false triggers during state transitions such as
loading screens.
"""

import win32gui
from pxl_lib import ColorCondition
from ansi import *


class PxlWinCheck:

    def __init__( self, config ):
        """
        Args:
            config (dict): normalized `wincheck` profile section: `target_window` plus a `markers`
                list of { x, y, color, tolerance }. Markers guard against inadvertent reactions, so
                their tolerance defaults to 0 (exact match) at load time; all must pass (AND).
        """
        self.target_app = config[ 'target_window' ]
        self.markers = [
            ColorCondition( m[ 'x' ], m[ 'y' ], m[ 'color' ], m[ 'tolerance' ] )
            for m in config[ 'markers' ]
        ]

    def marker_ok( self ):
        return all( marker.passes() for marker in self.markers )

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
