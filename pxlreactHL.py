"""
pxlreactHL.py is a variant of the PxlReact project which strips the tkinter GUI elements and uses a
lighter weight command line interface.

This is the project's main module which is responsible for assigning reactions to pixels and then
polling those pixels for changes.
"""
import keyboard
import ctypes
import time

from concurrent.futures import ThreadPoolExecutor
import threading

from pxl_winwatch import PxlWinWatch
from pxl_intercept import PxlIntercept

from pxl_lib import *
from ansi import *

# Define keybinds for PxlReact
KEYBINDS = {
    "f12": lambda app: app.exit_application()
}

class PxlReactApp:
    """
    PxlReactApp is the main application class for the PxlReact project; it initializes the GUI and manages the list of
    pixels being monitored (formerly PxlWatcher).
    """

    def __init__( self ):
        """
        Args:
            pixel_count (int): Maximum number of pixels we will monitor
            tick_interval (float): How often (in seconds) to poll for pixel color changes; longer
                intervals may miss rapid changes
        """

        # Window watch (replaces old 'check_session' method with its 'active' flag)
        self.winwatch = PxlWinWatch()

        self.PI = PxlIntercept( self )

        self.pixel_count = 2
        self.tick_interval = 0.025
        self.stop_event = threading.Event()

        # Initialize the list; index 0 is unused in lite (no mouse preview)
        self.pixels = [ None ] * ( self.pixel_count + 1 )

        # Add regular pixels starting at index 1; assign arbitrary initial pixel coordinates and
        # pass a reference to ourselves so Pxl's can remember us
        for i in range( 1, self.pixel_count + 1 ):
            self.pixels[ i ] = Pxl( i, i * 11, i * 11, app = self )

        self.registry = PxlReactionRegistry( self )

        self.load_reaction( 1, "HP1" )
        self.load_reaction( 2, "MP1" )

        for key_combination, action in KEYBINDS.items():
            keyboard.add_hotkey( key_combination, action, args = [ self ] )

    def start_update_loop( self ):
        """
        Main update loop without GUI. Blocks and polls pixels at the configured interval.
        """
        try:
            while not self.stop_event.is_set():
                if self.winwatch.active:
                    for pxl in self.pixels[ 1: ]:
                        if pxl is None:
                            continue
                        pxl.update_color()
                time.sleep( self.tick_interval )
        except KeyboardInterrupt:
            self.stop_event.set()
        finally:
            self.cleanup()

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

        pxl.update_color()

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
            raise ValueError( f"Reaction '{reaction_name}' not found in registry" )

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
        rx = reaction_data['sx']
        ry = reaction_data['sy']
        print( f"[{pixel_index}] {BLUE}{reaction_name}{RESET} @ ({rx}, {ry})" )

    def exit_application( self ):
        """
        Exit the application cleanly, releasing resources.
        """
        self.stop_event.set()

    def cleanup( self ):
        """
        Clean up resources and background workers. Safe to call multiple times.
        """
        global HDC
        print( f"{RED}Exiting...{RE}" )
        try:
            keyboard.clear_all_hotkeys()
            keyboard.unhook_all()
        except Exception:
            pass

        try:
            # Prevent new reaction submissions, then shut down reaction executor
            PxlReaction.pxl_exec.shutdown( wait = False, cancel_futures = True )
        except Exception:
            pass

        try:
            self.PI.close()
        except Exception:
            pass

        try:
            ctypes.windll.user32.ReleaseDC( 0, HDC )
        except Exception:
            pass


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

        self.reaction = None

        # Perform an initial update to set the Pxl's color after assignment or loading from file
        self.update_color()

    def update_color( self ):
        """
        Poll the color at this Pxl's location; updating its properties and checking if it should
        trigger a reaction.
        """

        screen_rgb = get_pixel_color( self.sx, self.sy )

        if screen_rgb and screen_rgb != self.rgb:
            self.rgb = screen_rgb

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
        if self.state != "ready" or not self.pxl.app.winwatch.active:
            return False

        return colors_different( self.pxl.rgb, self.reaction_color )

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
    hp_cooldown = 2.8
    mp_cooldown = 2.3

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
        print( f"+❤️" )

    def react_MP( self ):
        self.app.PI.press( "2" )
        print( f"+✨" )

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
    app.start_update_loop()

