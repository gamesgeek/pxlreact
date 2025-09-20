import tkinter as tk
from pxl_gui import PxlGui
import pxl_guiconst as pgc
from pxl_guiconst import TEXT_COLOR, BG_COLOR, LINE_COLOR, FONT, TEXT_SIZE, WIN_POS
from pxl_intercept import PxlIntercept
import keyboard
import ctypes
import time
from concurrent.futures import ThreadPoolExecutor

# pxl_lib includes JSON functions and ANSI color for s
from pxl_lib import *
from ansi import *

# Install pywin32 for this
import win32gui

# Temporary global to store the name of the last active window scanned before a trigger
# fires (i.e., for debugging when triggers fire outside the intended environment))
LAST_WIN = ''

# Position & RGB values for reference pixels at various screen locations for checking which state
# the game is in.

CHAT_BUBBLE_X = 19
CHAT_BUBBLE_Y = 1081
CHAT_BUBBLE_COLOR = ( 163, 156, 126 )

# Define keybinds for PxlReact
KEYBINDS = {
    "ctrl+f1": lambda app: app.reassign_pixel( 1 ),
    "ctrl+f2": lambda app: app.reassign_pixel( 2 ),
    "ctrl+f3": lambda app: app.reassign_pixel( 3 ),
    "ctrl+f4": lambda app: app.reassign_pixel( 4 ),

    "alt+f5": lambda app: app.load_reaction( 1, "HP1" ),
    "alt+f6": lambda app: app.load_reaction( 2, "MP1" ),

    # New: update reaction target/color from the pixel under the mouse
    "ctrl+h": lambda app: app.registry.update_reaction_by_mouse( "HP1" ),
    "ctrl+m": lambda app: app.registry.update_reaction_by_mouse( "MP1" ),

    "f11": lambda app: app.test_attack_sequence(),

    "f12": lambda app: app.exit_application()
}


class PxlReactApp:
    """
    PxlReactApp is the main application class for the PxlReact project; it initializes the GUI and manages the list of
    pixels being monitored (formerly PxlWatcher).
    """

    def __init__( self, pixel_count = 4, tick_interval = 25 ):
        """
        Args:
            pixel_count (int):   Maximum number of pixels we will monitor; determines the size of the pixel display area
                                 "grid" which are all areas except the mouse preview.
            tick_interval (int): How often to poll for pixel color changes; longer intervals may miss rapid changes or
                                 allow the mouse to "skip" pixels when in motion.
        """
        self.session_active = False

        self.PI = PxlIntercept()
        self.pixel_count = pixel_count
        self.tick_interval = tick_interval

        # Initialize the list and add the mouse pixel at index 0
        self.pixels = [ None ] * ( pixel_count + 1 )
        self.pixels[ 0 ] = Pxl( index = 0 ) # Mouse preview pixel

        # Add regular pixels starting at index 1; assign arbitrary initial pixel coordinates and
        # pass a reference to ourselves so Pxl's can remember us
        for i in range( 1, pixel_count + 1 ):
            self.pixels[ i ] = Pxl( i, i * 11, i * 11, app = self )

        # PxlGui initializes a layout_config dict which provides settings to size & position elements
        self.gui = PxlGui()
        self.root = tk.Tk()

        self.canvas = tk.Canvas(
            self.root,
            width = self.gui.layout_config[ "window" ][ "width" ],
            height = self.gui.layout_config[ "window" ][ "height" ],
            bg = self.gui.layout_config.get( "background_color", "#000000" )
        )

        # Configure the tkinter window to be title-less, always on top, non-resizable
        self.root.overrideredirect( True )
        self.root.title( "pxlreact" )
        self.root.attributes( "-topmost", True )
        self.root.resizable( False, False )

        # Position the window at the lower-right corner of the left-hand monitor
        self.root.geometry( WIN_POS )

        self.canvas.pack( fill = tk.BOTH, expand = True )

        self.registry = PxlReactionRegistry( self )

        # Create GUI components
        self.init_gui_elements()

        for key_combination, action in KEYBINDS.items():
            # Bind the key combination to the action
            keyboard.add_hotkey( key_combination, action, args = [ self ] )

        # Start the main update loop
        self.start_update_loop()
        self.logging_active = False
        self.log_start_time = None

    def toggle_pixel_testing( self ):
        """
        Toggle pixel testing mode.
        """
        self.logging_active = not self.logging_active
        if self.logging_active:
            self.log_start_time = time.time()
            print( f"{GREEN}Logging pixels...{RE}" )
        else:
            self.print_test_summary()
            print( f"{RED}Logging stopped...{RE}" )

    def start_update_loop( self ):
        """
        Main update loop, extended to log pixel changes if logging is active.
        """

        def update():
            self.check_session()
            if self.session_active:
                self.track_mouse()
                for pxl in self.pixels:
                    pxl.update_color()
                    if pxl.updated:
                        self.redraw_display_area( pxl )
                        pxl.updated = False

            self.root.after( self.tick_interval, update )

        update()

    def check_session( self ):
        """
        Check if the session is active and update the session_active state.
        """
        global LAST_WIN
        self.session_active = True
        return
        # Make sure the currently active window shares a title with the application we're testing
        active_window = win32gui.GetForegroundWindow()
        LAST_WIN = win32gui.GetWindowText( active_window )
        window_active = ( LAST_WIN == 'Path of Exile 2' )

        # Validate static pixels at two key locations to ensure we're in the right "state" to
        # send input.
        chat_bubble_good = validate_color_at( CHAT_BUBBLE_X, CHAT_BUBBLE_Y, CHAT_BUBBLE_COLOR )

        self.session_active = window_active and chat_bubble_good

    def init_gui_elements( self ):
        """
        Initialize GUI elements for mouse preview and pixel displays.
        """
        layout = self.gui.layout_config

        # The "mouse preview area" displays information about the pixel under the mouse cursor and is updated
        # continuously; it is positioned on the top row of the GUI window above the assigned pixels.
        self.create_display_area( layout[ "mouse_preview" ], "mouse_preview" )

        # Initialize pixel areas
        for i, area in enumerate( layout[ "pixel_areas" ], start = 1 ):
            self.create_display_area( area, f"pixel_{i}" )

    def create_display_area( self, area, tag_prefix ):
        """
        Helper to create a display area in the GUI.
        """
        # Where da = display_area... get the corners of a rectangle that surrounds the area
        da_left = area[ "x1" ]
        da_top = area[ "y1" ]
        da_right = area[ "x2" ]
        da_bottom = area[ "y2" ]

        # Where dt = data_text... position data text PAD pixels from the top-left corner
        dt_left = da_left + pgc.PAD
        dt_top = da_top + pgc.PAD

        # Where bp = big_pixel... position the big pixel PAD pixels from the top-right corner
        bp_left = da_right - pgc.PAD - pgc.BIG_PXL_DIM
        bp_top = da_top + pgc.PAD
        bp_right = bp_left + pgc.BIG_PXL_DIM
        bp_bottom = bp_top + pgc.BIG_PXL_DIM

        # Draw the area border
        self.canvas.create_rectangle(
            da_left, da_top, da_right, da_bottom, outline = LINE_COLOR, tags = f"{tag_prefix}_area"
        )

        # Create & position the pixel data text
        self.canvas.create_text(
            dt_left,
            dt_top,
            text = "",
            anchor = "nw",
            fill = TEXT_COLOR,
            font = ( FONT, TEXT_SIZE ),
            tags = f"{tag_prefix}_text"
        )

        # Create the big pixel
        self.canvas.create_rectangle(
            bp_left,
            bp_top,
            bp_right,
            bp_bottom,
            fill = BG_COLOR,
            outline = pgc.BIG_PXL_FRAME,
            tags = f"{tag_prefix}_big_pxl"
        )

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
        # ( "PxlReact.reassign_pixel", index, x, y )
        # Make sure the Pxl object's color is updated immediately after assignment so the GUI will reflect it
        pxl.update_color()

    def redraw_display_area( self, pxl ):
        """
        Redraw the GUI display area associated with a Pxl object using its index.
        """
        tag_prefix = "mouse_preview" if pxl.index == 0 else f"pixel_{pxl.index}"
        self.canvas.itemconfig( f"{tag_prefix}_text", text = f"({pxl.sx}, {pxl.sy})\n{pxl.hex}\n{pxl.rgb}" )
        self.canvas.itemconfig( f"{tag_prefix}_big_pxl", fill = pxl.hex )

    def track_mouse( self ):
        """
        Make sure the mouse preview area redraws any time the cursor moves (even if the color doesn't change)
        """
        mpxl = self.pixels[ 0 ]
        mx, my = get_mouse_pos()
        if mx != mpxl.sx or my != mpxl.sy:
            mpxl.sx, mpxl.sy = mx, my
            mpxl.updated = True

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
            raise ValueError( f"Reaction '{reaction_name}' not found in registry." )

        # Reassign the pixel to monitor the sx, sy coordinates from the reaction definition
        self.reassign_pixel( pixel_index, x = reaction_data[ 'sx' ], y = reaction_data[ 'sy' ] )

        # Assign the reaction to the pixel
        pixel = self.pixels[ pixel_index ]
        pixel.set_reaction(
            PxlReaction(
                pxl = pixel,
                reaction_type = reaction_data[ 'type' ],
                reaction_color = reaction_data[ 'reaction_color' ],
                reaction = reaction_data[ 'reaction' ],
                cooldown = reaction_data.get( 'cooldown', 0.5 )
            )
        )
        print(
            f"Assigned reaction '{reaction_name}' to pixel {pixel_index}, now monitoring ({reaction_data['sx']}, {reaction_data['sy']})."
        )

    def loop_key( self, key, delay = 0.1 ):
        """
        Replace loop_space with a more generic loop_key method that can send any key presses any key
        on a set interval/delay between each press
        """
        print( f"{GREEN}Pressing {key} every {delay} seconds...{RE}" )
        while not keyboard.is_pressed( "r" ):
            self.PI.press( key )
            time.sleep( delay )
        print( f"{RED}Stopped pressing {key}.{RE}" )

    def loop_space( self, delay ):
        """
        Simple method to send "space" key presses with a set interval/delay between each press; 
        invoking this method while looping should stop the loop and return.
        """
        print( f"{GREEN}Pressing space every {delay} seconds...{RE}" )
        while not keyboard.is_pressed( "esc" ):
            self.PI.press( "space" )
            time.sleep( delay )
        print( f"{RED}Stopped pressing space.{RE}" )

    def run( self ):
        """
        Run the main GUI loop.
        """
        self.root.mainloop()
    
    def exit_application( self ):
        """
        Exit the application cleanly, releasing resources and closing the GUI.
        """
        global HDC
        print( f"{RED}Exiting...{RE}" )
        self.PI.close()
        ctypes.windll.user32.ReleaseDC( 0, HDC )
        self.root.destroy()


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
        self.hex = None
        self.updated = False
        self.reaction = None

        # Perform an initial update to set the Pxl's color after assignment or loading from file
        self.update_color()

    def update_color( self ):
        """
        Poll the color at this Pxl's location; updating its properties if the color is different than current values and
        setting updated flag so other classes will know we changed.
        """
        screen_rgb = get_pixel_color( self.sx, self.sy )
        if screen_rgb and screen_rgb != self.rgb:
            # if self.index > 0:
            #     # Skip reporting color changes under the mouse to reduce spam during testing
            self.rgb = screen_rgb
            self.hex = rgb_to_hex( self.rgb )
            self.updated = True
            # If the updated pixel has an assigned reaction, check to see if we need to trigger it
            if self.reaction is not None and self.reaction.should_trigger():
                self.reaction.trigger()

    def set_reaction( self, pixel_reaction ):
        """
        Assign a reaction to this pixel.

        Args:
            pixel_reaction (PxlReaction): Reaction object defining how this pixel reacts to changes.
        """
        self.reaction = pixel_reaction


class PxlReaction:
    """
    Defines a reaction for a monitored pixel, specifying conditions and behavior when the reaction triggers.

    A ThreadPoolExecutor will manage the submission of reactions to respect cooldown periods and prevent overlapping
    reactions.
    """

    pxl_exec = ThreadPoolExecutor( max_workers = 4, thread_name_prefix = "PxlReaction" )

    def __init__( self, pxl, reaction_type, reaction_color, reaction, cooldown = 0.5 ):
        """
        Initialize a PxlReaction instance.

        Args:
            pixel_index (int): The index of our "parent" Pxl (i.e., the one that determines if we trigger)
            reaction_type (str): Type of reaction (e.g., "react_if_color"). 
            reaction_color (tuple[int, int, int]): Target RGB color for the reaction.
            reaction (callable): Function to execute when the reaction triggers.
            cooldown (float, optional): Cooldown time in seconds; default 0.5
        """
        self.pxl = pxl
        self.type = reaction_type
        self.reaction_color = reaction_color
        self.cooldown = cooldown
        self.reaction = reaction
        self.state = "ready"
        self.last_trigger_time = 0

    def should_trigger( self ):
        """
        Compare an observerd color against this PxlReaction's trigger type and color to see if a reaction should trigger.
        """
        # Trigger only when we're ready and our parent app session is active (in the right window, etc.)
        if self.state != "ready" or not self.pxl.app.session_active:
            return False

        if self.type == "react_if_not_color":
            triggering = colors_different( self.pxl.rgb, self.reaction_color )
        elif self.type == "react_if_color":
            triggering = colors_similar( self.pxl.rgb, self.reaction_color )

        if triggering:
            print( f'  [{GREEN}*{RE}] {self.pxl.rgb} ~= {self.reaction_color}{RE}' )

        return triggering

    def trigger( self ):
        """
        Call the reaction function then put this reaction into cooldown for the set duration.
        """
        self.reaction()
        self.state = "cooldown"
        self.pxl_exec.submit( self.cooldown_and_reset )

    def cooldown_and_reset( self ):
        """
        Reset the reaction state to "ready" after the cooldown period has elapsed.
        """
        time.sleep( self.cooldown )
        self.state = "ready"
        # When a reaction comes off cooldown, check to see if it's pixel is in a trigger state
        if self.should_trigger():
            self.trigger()


class PxlReactionRegistry:

    reaction_types = [ "react_if_color", "react_if_not_color" ]

    # The color of the pixels to look for to ensure we're "healthy and energetic"
    hp_reaction_color = (167, 34, 46)
    mp_reaction_color = (16, 53, 111)

    # How long our flasks take to recharge (don't try to use them more often than this)
    hp_cooldown = 4
    mp_cooldown = 2.5

    def __init__( self, app ):
        """
        Class to hold a registry of predefined reactions that can be assigned to pixels.
        """

        # Safeguard against random typos that have gotten me killed before...
        if self.hp_cooldown > 5 or self.mp_cooldown > 5:
            raise ValueError( f"Flask cooldowns: {self.hp_cooldown}/{self.mp_cooldown}" )

        self.app = app

        self.reactions_registry = {
            'HP1': {
                'sx': 134,
                'sy': 1275,
                'type': 'react_if_not_color',
                'reaction_color': self.hp_reaction_color,
                'cooldown': self.hp_cooldown,
                'reaction': self.react_HP
            },
            'MP1': {
                'sx': 2400,
                'sy': 1364,
                'type': 'react_if_not_color',
                'reaction_color': self.mp_reaction_color,
                'cooldown': self.mp_cooldown,
                'reaction': self.react_MP
            }
        }

        self.validate_registry()

    def react_HP( self ):
        self.app.PI.press( "1" )
        print( f"+|{GREEN}Attemping HP Flask{RE}| ({CYAN}{LAST_WIN}{RE})" )

    def react_MP( self ):
        self.app.PI.press( "2" )
        print( f"+|{BLUE}Attemping MN Flask{RE}| ({CYAN}{LAST_WIN}{RE})" )


    def update_reaction_by_mouse( self, reaction_name ):
        """
        Capture the mouse (x, y) immediately, then wait ~2s before sampling the color
        at that position. Update the named reaction's sx, sy, and reaction_color.
        If any active pixel is using this reaction, update it in place and refresh.
        """
        mx, my = get_mouse_pos()
        print( f"{CYAN}Locked coordinates for {reaction_name}: ({mx}, {my}) — waiting 2s...{RE}" )
        time.sleep( 2.0 )

        rgb = get_pixel_color( mx, my )
        if not rgb:
            print( f"{RED}update_reaction_by_mouse: could not read color at ({mx}, {my}){RE}" )
            return

        entry = self.reactions_registry.get( reaction_name )
        if not entry:
            print( f"{RED}update_reaction_by_mouse: unknown reaction '{reaction_name}'{RE}" )
            return

        old_sx, old_sy = entry[ 'sx' ], entry[ 'sy' ]
        old_color = entry[ 'reaction_color' ]

        # Update the registry entry
        entry[ 'sx' ] = mx
        entry[ 'sy' ] = my
        entry[ 'reaction_color' ] = rgb

        print(
            f"{YELLOW}{reaction_name}{RE} updated "
            f"({old_sx}, {old_sy}) {old_color}  ->  ({mx}, {my}) {rgb}"
        )

        # If any pixel currently uses this reaction, update it in-place
        for pxl in self.app.pixels:
            if not pxl or not pxl.reaction:
                continue

            if pxl.reaction.reaction is entry[ 'reaction' ]:
                pxl.sx = mx
                pxl.sy = my
                pxl.reaction.reaction_color = rgb
                pxl.update_color()
                self.app.redraw_display_area( pxl )

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

            # Validate `cooldown`
            cooldown = reaction.get( 'cooldown', 0 )
            if not ( 0 < cooldown < 180 ): # avoid ms/s confusion with cooldowns (never > 3 minutes)
                raise ValueError( f"Unreasonable 'cooldown' for reaction '{name}': {cooldown}" )

            # Validate `reaction` as a callable
            if not callable( reaction.get( 'reaction' ) ):
                raise ValueError( f"Invalid 'reaction' for reaction '{name}': Must be a callable." )


if __name__ == "__main__":
    app = PxlReactApp()
    app.run()

