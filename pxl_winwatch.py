"""
PxlWinWatch is a single-purpose class designed to provide an "active" flag to the rest of the project
for filtering reactions and events when outside of the desired application and context.
"""

import win32gui
from pxl_lib import validate_color_at
import threading

class PxlWinWatch:

    def __init__( self ):

        # Check every interval seconds (slower than PxlReact's polling rate)
        self.interval = 0.2

        # The primary functional goal of PxlWinWatch is keeping this flag accurate
        self.active = False

        # The application we're monitoring; must be the active window
        self.target_app = 'Path of Exile 2'

        self.marker_x = 21
        self.marker_y = 1084
        self.marker_color = ( 129, 121, 91 )

        self._stop_event = threading.Event()
        self._thread = None

        # Start ourselves automatically on init
        self.start()

    def marker_ok( self ):
        return validate_color_at( self.marker_x, self.marker_y, self.marker_color )

    def in_target_app( self ):
        return self.target_app == win32gui.GetWindowText( win32gui.GetForegroundWindow() )

    def update( self ):
        self.active = self.in_target_app() and self.marker_ok()

    def update_slow( self ):
        """
        Debug version of update that will tell us why the app is inactive; use if this stops working,
        which sometimes happens after updates or with overlay apps that make subtle color changes.
        """
        in_app = self.in_target_app()
        marker_ok = self.marker_ok()
        print( f"PxlWinWatch: app: {in_app} marker: {marker_ok}" )
        self.active = in_app and marker_ok

    def start( self ):
        # Avoid starting ourselves if we're already running
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread( target = self._run, name = 'PxlWinWatch', daemon = True )
        self._thread.start()

    def stop( self ):
        if not self._thread:
            return
        self._stop_event.set()

    def _run( self ):
        while not self._stop_event.is_set():
            self.update()
            self._stop_event.wait( self.interval )
