# def test_move( self ):
#     """
#     Test mouse movement.
#     """
#     move_points = self.find_grid( 1696, 788, 2537, 1138, 5, 12 )
#     # For each point within the move_points list, invoke pyint.move_to separated by a random delay of 100-200ms
#     for point in move_points:
#         pyint.move_to( point[ 0 ], point[ 1 ] )
#         time.sleep( random.uniform( 1, 2 ) )

# def find_grid( self, tlx, tly, brx, bry, rows, cols ):
#     """
#     Generate random (x, y) coordinates within each square of a defined grid.

#     Args:
#         tlx (int): Top-left x-coordinate of the grid.
#         tly (int): Top-left y-coordinate of the grid.
#         brx (int): Bottom-right x-coordinate of the grid.
#         bry (int): Bottom-right y-coordinate of the grid.
#         rows (int): Number of rows in the grid.
#         cols (int): Number of columns in the grid.

#     Returns:
#         list of tuples: A list containing (x, y) coordinates, one for each square.
#     """
#     # Compute the width and height of each cell
#     cell_width = ( brx - tlx ) / cols
#     cell_height = ( bry - tly ) / rows

#     points = []
#     for row in range( rows ):
#         for col in range( cols ):
#             # Calculate the bounds of the current cell
#             cell_x_min = tlx + col * cell_width
#             cell_x_max = cell_x_min + cell_width
#             cell_y_min = tly + row * cell_height
#             cell_y_max = cell_y_min + cell_height

#             # Generate a random point within this cell
#             x = random.uniform( cell_x_min, cell_x_max )
#             y = random.uniform( cell_y_min, cell_y_max )

#             points.append( ( int( x ), int( y ) ) ) # Convert to integer pixels

#     return points

# def cast_map( self ):
#     with pyint.hold_key( "x" ):
#         self.press( "up" )
#         self.press( "down" )
#         self.press( "right" )

# def open_gate( self ):
#     with pyint.hold_key( "x" ):
#         self.press( "right" )
#         self.press( "down" )
#         self.press( "down" )
#         self.press( "down" )

# def minor_heal( self ):
#     # Cast minor heal with right-up-left-up-up
#     with pyint.hold_key( "x" ):
#         self.press( "right" )
#         self.press( "up" )
#         self.press( "left" )
#         self.press( "up" )
#         self.press( "up" )

# def auto_run( self ):
#     with pyint.hold_key( "w" ):
#         time.sleep( 30 )

# def test_mouse_circle( self ):
#     """
#     Move the mouse in a circle around the center (cx, cy),
#     starting/ending at (x0, y0).  The circle is sampled at num_points
#     points.  We wait 'rate' seconds between successive points to
#     control the movement speed.

#     Assumes 'self.pyint.move_to(x, y)' moves the mouse to (x,y).
#     """

#     rate = 0.002

#     # Generate the points of the circle
#     pts = circle_points()

#     for ( mx, my ) in pts:
#         # Move the mouse to the next point
#         pyint.move_to( int( mx ), int( my ) )

#         # Sleep briefly so the mouse doesn't rush too fast
#         time.sleep( rate )

# def timed_repress( self, key, delay ):
#     """
#     Press a key immediately, then after a given delay press it again.
#     """
#     self.press( key )
#     time.sleep( delay )
#     winsound.PlaySound( ALERT_SOUND, winsound.SND_FILENAME )

# def click_hold( self, t ):
#     """
#     Clicks the left mouse button down, holds it for 't' seconds, then releases it.
#     """
#     pyint.mouse_down( "left" )
#     time.sleep( t )
#     pyint.mouse_up( "left" )

# def click_hold_move( self, t, d ):
#     """
#     1. Click and hold the mouse button for a certain period of time
#     2. then move the mouse along the y axis either up or down
#     """
#     self.click_hold( t )
#     time.sleep( 0.66 )
#     pyint.move_relative( 0, d )

# def move_toward_center_right( self ):

#     rate = 3

#     while True:
#         pyint.move_to( MAX_X, MAX_Y // 2 )
#         time.sleep( rate )

# def test_mouse_move( self ):
#     self.PI.test_move()

# def cast_map( self ):
#     self.PI.cast_map()

# def open_gate( self ):
#     self.PI.open_gate()

# def minor_heal( self ):
#     self.PI.minor_heal()

# def test_circle( self ):
#     self.PI.move_toward_center_right()

# def repress( self, key, delay ):
#     self.PI.timed_repress( key, delay )

# def auto_run( self ):
#     self.PI.auto_run()

# def click_moveup( self ):
#     self.PI.click_hold_move( 0.9, 111 )

# def click_movedown( self ):
#     self.PI.click_hold_move( 0.8, -111 )

# import os
# from pathlib import Path


# def rename_mp4s_by_creation_date( directory_path ):
#     directory = Path( directory_path )
#     mp4_files = [ f for f in directory.glob( "*.mp4" ) if f.is_file() ]

#     # Sort files by creation time
#     mp4_files.sort( key = lambda f: f.stat().st_birthtime )

#     # Rename files sequentially
#     for index, file in enumerate( mp4_files, start = 1 ):
#         new_name = directory / f"{index}.mp4"
#         file.rename( new_name )


# # Example usage:
# # rename_mp4s_by_creation_date( r"C:\Users\12404\Videos\NVIDIA\Path of Exile 2" )
# TEST_PIXELS = [
#     {
#         'tx': 168,
#         'ty': 1370,
#         'base_color': ( 74, 15, 20 ),
#         'max_color': -1,
#         'max_diff': 0,
#         'average_diff': 0,
#         'changes': 0,
#         'diff_log': [],
#     },
#     {
#         'tx': 154,
#         'ty': 1367,
#         'base_color': ( 80, 21, 24 ),
#         'max_color': -1,
#         'max_diff': 0,
#         'average_diff': 0,
#         'changes': 0,
#         'diff_log': [],
#     },
#     {
#         'tx': 140,
#         'ty': 1363,
#         'base_color': ( 79, 25, 27 ),
#         'max_color': -1,
#         'max_diff': 0,
#         'average_diff': 0,
#         'changes': 0,
#         'diff_log': [],
#     },
#     {
#         'tx': 151,
#         'ty': 1357,
#         'base_color': ( 82, 21, 24 ),
#         'max_color': -1,
#         'max_diff': 0,
#         'average_diff': 0,
#         'changes': 0,
#         'diff_log': [],
#     },
# ]


# class ClickCycler:
#     """
#     Periodically checks a list of screen coords; if the pixel there matches
#     any of the given colors, it moves the mouse and clicks asynchronously.
#     """

#     def __init__( self, coords, colors, interval = 0.1 ):
#         self.coords = coords
#         self.colors = colors
#         self.interval = interval # seconds between checks
#         self._stop_event = Event()
#         self._thread = Thread( target = self._run, daemon = True )

#     def start( self ):
#         """Launch the background checking thread."""
#         if not self._thread.is_alive():
#             self._stop_event.clear()
#             self._thread = Thread( target = self._run, daemon = True )
#             self._thread.start()

#     def stop( self ):
#         """Signal the thread to exit and wait for it."""
#         self._stop_event.set()
#         self._thread.join()

#     def _run( self ):
#         """Loop until stopped, checking each coord for a match, then clicking."""
#         while not self._stop_event.is_set():
#             for x, y in self.coords:
#                 pyint.move_to( x, y )
#                 pix = get_pixel_color( x, y )
#                 time.sleep( 1 )
#                 print( f"Checking pixel at ({x}, {y}): {pix}" )
#                 if pix is None:
#                     # couldn't read the pixel—skip to next coord
#                     continue

#                 for target in self.colors:
#                     if colors_similar( pix, target ):
#                         pyint.left_click( x, y )
#                         break
#             time.sleep( self.interval )

    # def exit_application( self ):
    #     global HDC
    #     print( f"{RED}Exiting...{RE}" )

    #     # 1) Stop Tk scheduling first so no more work gets enqueued
    #     self.stop_update_loop()

    #     # 2) Unhook & kill hotkey threads
    #     if hasattr( self, 'hotkeys' ):
    #         self.hotkeys.close()

    #     # 3) Stop ALL executors so their non-daemon threads don't block process exit
    #     try:
    #         self.PI.tpexec.shutdown( wait = False, cancel_futures = True )
    #     except TypeError:
    #         self.PI.tpexec.shutdown( wait = False )

    #     try:
    #         PxlReaction.shutdown_executor()
    #     except Exception:
    #         pass

    #     # 4) Release Win32 DC if you actually created HDC; guard if it's not set
    #     try:
    #         ctypes.windll.user32.ReleaseDC( 0, HDC )
    #     except Exception:
    #         pass

    #     # 5) Tear down Tk cleanly
    #     try:
    #         self.root.quit()
    #     except Exception:
    #         pass
    #     self.root.destroy()

# class KeyCycler:
#     """
#     Block key input to intercept a specified "cycler" key; when the cycler is pressed, send the next
#     key in a predefined sequence, observing per-key cooldowns and an optional reset timeout.

#     Each element of sequence is a tuple (key_name, cooldown_seconds). The cycler will only send
#     that key if at least cooldown_seconds have elapsed since its last send. If timeout is None
#     or non-positive, the sequence position will never reset based on elapsed time.

#     Attributes:
#         key_name (str): Name of the key to intercept (default 'l').
#         sequence (list of (str, float)): Ordered list of (key_name, cooldown_secs).
#         timeout (float or None): Reset timeout in seconds (default None, meaning no timeout).
#     """

#     def __init__( self, interceptor, key_to_cycle = 'l', sequence = None, timeout = None ):

#         self.pi = interceptor

#         # Cycler key
#         self.key_name = key_to_cycle
#         self.key_code = SCAN_CODES[ self.key_name ]

#         # Sequence: list of (key_name, cooldown)
#         self.sequence = sequence or []
#         # Precompute scan codes and cooldown lists
#         self.sequence_codes = [ SCAN_CODES[ k ] for k, _ in self.sequence ]
#         self.cooldowns = [ cd for _, cd in self.sequence ]
#         # Track last-pressed timestamps per sequence entry
#         self.last_pressed = [ 0.0 ] * len( self.sequence )

#         # Optional reset timeout (None or <=0 means never reset)
#         self.timeout = timeout
#         # Sequence index and last press time
#         self.index = 0
#         self.last_time = None

#         # Interception context: only filter our key-down events
#         self.ctx = Interception()
#         self.ctx.set_filter( self.ctx.is_keyboard, FilterKeyFlag.FILTER_KEY_DOWN )
#         self.active = False
#         self.thread = None

#     def start_intercepting( self ):
#         """Begin the interception loop in a daemon thread."""
#         if self.active:
#             return
#         print( f"KeyCycler intercepting: {self.key_name}..." )
#         self.active = True
#         self.thread = Thread( target = self._intercept_loop, daemon = True )
#         self.thread.start()

#     def stop_intercepting( self ):
#         """Stop interception and clean up."""
#         self.active = False
#         if self.thread:
#             self.thread.join()
#         self.ctx.destroy()

#     def _get_next_index( self, now ):
#         """
#         Find next sequence index whose cooldown has elapsed. Reset sequence if timeout configured and passed.
#         Returns None if no key is currently eligible.
#         """
#         # If a positive timeout is set, and enough time has passed since last cycle action, reset index
#         if self.timeout and self.timeout > 0:
#             if self.last_time is None or ( now - self.last_time ) > self.timeout:
#                 self.index = 0

#         # Search full cycle for an eligible key
#         n = len( self.sequence_codes )
#         for offset in range( n ):
#             idx = ( self.index + offset ) % n
#             if ( now - self.last_pressed[ idx ] ) >= self.cooldowns[ idx ]:
#                 return idx
#         return None

#     def _send_key( self, code ):
#         """Helper to send a down/up stroke for a scan-code."""
#         down = ks( code, KeyFlag.KEY_DOWN )
#         up = ks( code, KeyFlag.KEY_UP )
#         self.ctx.send( PRIMARY_KEYBOARD, down )
#         self.ctx.send( PRIMARY_KEYBOARD, up )

#     def _intercept_loop( self ):
#         """Core loop that waits for inputs and handles cycling logic."""
#         try:
#             while self.active:
#                 hid = self.ctx.await_input()
#                 stroke = self.ctx.devices[ hid ].receive()

#                 # Only intercept if session active, our key, and key-down event
#                 if stroke.code == self.key_code and stroke.flags == KeyFlag.KEY_DOWN:
#                     now = time.time()
#                     idx = self._get_next_index( now )
#                     if idx is not None:
#                         # Send eligible key and update state
#                         send_code = self.sequence_codes[ idx ]
#                         self._send_key( send_code )
#                         self.last_pressed[ idx ] = now
#                         # Advance and wrap for next cycle
#                         self.index = ( idx + 1 ) % len( self.sequence_codes )
#                         self.last_time = now
#                     # else: no eligible key; drop the event
#                 else:
#                     # Forward all other events unmodified
#                     self.ctx.send( hid, stroke )

#         except Exception as e:
#             print( f"Error in KeyCycler intercept loop: {e}" )


# class KeyHolder:
#     """
#     A class for managing hold-and-release behavior for a single key in the PxlReact application.
#     """

#     def __init__( self, key_to_hold, min_hold_time, max_hold_time, pxlreact_app ):

#         self.app = pxlreact_app

#         self.key_name = key_to_hold
#         self.key_code = SCAN_CODES[ self.key_name ]

#         self.hold_stroke = ks( self.key_code, KeyFlag.KEY_DOWN )
#         self.release_stroke = ks( self.key_code, KeyFlag.KEY_UP )

#         # Create an Interception context
#         self.hold_context = Interception()
#         self.hold_context.set_filter(
#             self.hold_context.is_keyboard, FilterKeyFlag.FILTER_KEY_DOWN | FilterKeyFlag.FILTER_KEY_UP
#         )

#         # Precomputed hold times
#         self.hold_times = self._precompute_hold_times( min_hold_time, max_hold_time )
#         self.hold_time_index = 0
#         # Active state and thread management
#         self.active = False
#         self.hold_thread = None
#         self.cancel_event = Event()

#     def _precompute_hold_times( self, min_time, max_time ):
#         """
#         Precompute 1000 random hold times between min_time and max_time (in seconds).
#         Supports granular floating-point precision.
#         """
#         return [ round( random.uniform( min_time, max_time ), 4 ) for _ in range( 1000 ) ]

#     def _next_hold_time( self ):
#         """
#         Retrieve the next precomputed hold time.
#         """
#         hold_time = self.hold_times[ self.hold_time_index ]
#         self.hold_time_index = ( self.hold_time_index + 1 ) % len( self.hold_times )
#         return hold_time

#     def start_intercepting( self ):
#         """
#         Start intercepting the designated key in a separate thread.
#         """
#         self.active = True
#         self.cancel_event.clear()
#         self.hold_thread = Thread( target = self._intercept_loop, daemon = True )
#         self.hold_thread.start()

#     def stop_intercepting( self ):
#         """
#         Stop intercepting the key and clean up resources.
#         """
#         self.active = False
#         self.cancel_event.set()
#         if self.hold_thread:
#             self.hold_thread.join()
#         self.hold_context.destroy()

#     def _intercept_loop( self ):
#         """
#         Intercept loop to handle the specific key events.
#         """
#         try:

#             while self.active:

#                 hold_hid = self.hold_context.await_input()
#                 hold_stroke = self.hold_context.devices[ hold_hid ].receive()

#                 # Process only the designated key
#                 if self.app.session_active and hold_stroke.code == self.key_code:
#                     if hold_stroke.flags == KeyFlag.KEY_DOWN:
#                         self._async_start_hold()
#                     elif hold_stroke.flags == KeyFlag.KEY_UP:
#                         # Ignore the actual physical release; the release will occur asynchronously
#                         pass
#                 else:
#                     # Forward all other key events unmodified
#                     self.hold_context.send( hold_hid, hold_stroke )

#         except Exception as e:
#             print( f"Error in KeyHolder intercept loop: {e}" )

#     def _async_start_hold( self ):
#         """
#         Start a hold event asynchronously if not already holding.
#         """
#         if hasattr( self, '_holding_flag' ) and self._holding_flag:
#             print( f"\t[] {RED}Skipping repeat hold request{RE}" )
#             return

#         self._holding_flag = True
#         Thread( target = self._perform_hold, daemon = True ).start()

#     def _perform_hold( self ):
#         """
#         Perform the hold-and-release logic asynchronously.
#         """
#         try:
#             # Wait for the next random hold time delay
#             hold_time = self._next_hold_time()
#             # Send, hold (wait), then release
#             self.hold_context.send( PRIMARY_KEYBOARD, self.hold_stroke )
#             self.cancel_event.wait( hold_time )
#             self.hold_context.send( PRIMARY_KEYBOARD, self.release_stroke )
#             print( f'  {CYAN}held for {hold_time}' )
#         finally:
#             # Ensure the holding flag is reset
#             self._holding_flag = False

#     def cancel_hold( self ):
#         """
#         Cancel the current hold event and ensure the key is released.
#         """
#         self.cancel_event.set()
#         hold_stroke = ks( self.key_code, KeyFlag.KEY_UP )
#         self.hold_context.send( PRIMARY_KEYBOARD, hold_stroke )
#         print( f"Hold canceled for {self.key_name}, key released." )
# Set Bezier Curve parameters (for emulating human-like mouse movements)
# CP = bc.BezierCurveParams()
# bc.set_default_params( CP )

# class PxlKbd:

#     """
#     TODO
#     I want to adapt this into a more complete "keyboard handling" module -- on top of the PxlIntercept
#     class, PxlKbd should build 
#     """
#     def __init__( self ):
#         pass

# def write_json( data, filepath ):
#     """
#     Write dict to JSON
#     """
#     try:
#         with open( filepath, 'w' ) as file:
#             json.dump( data, file, indent = 2 )

#     except Exception as e:
#         print( f"Error writing JSON: {e}" )


# def read_json( filepath, mode = 'r' ):
#     """
#     Read JSON to dict
#     """
#     try:
#         with open( filepath, mode ) as file:
#             rawdata = json.load( file )
#             return rawdata

#     except Exception as e:
#         print( f"Error loading JSON file: {e}" )
#         return None
# def rgb_to_hex( rgb ):
#     """Convert an RGB tuple to a hexadecimal color."""
#     return "#{:02x}{:02x}{:02x}".format( *rgb )
