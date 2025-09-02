import random
import time
from itertools import cycle

from concurrent.futures import ThreadPoolExecutor

"""
pyinerception interacts with the interception driver.

Local & online references:
    - pyinterception_README.md
    - pyinterception_inputs.py
    - pyinterception.py
    - https://github.com/kennyhml/pyinterception
    - https://github.com/oblitum/Interception
"""
import interception as pyint
from interception.constants import FilterKeyFlag, KeyFlag

# ANSI colors and RESET for highlighting Terminal output
from ansi import *

pyint.auto_capture_devices( keyboard = True, mouse = False, verbose = True )

class PxlIntercept:

    """
    PxlIntercept encapsulates interactions with python-interception to send key events to applications
    and game clients that are received as if delivered from hardware.

    PxlIntercept uses asynchronous, non-blocking calls with the intent of supporting common use
    cases like "pressing one key while holding another" which are typical in games. 
    """

    def __init__( self, pxlreact_app ):

        self.pi_cfg = {
            'max_workers': 5,
            'min_press_delay': 50,
            'max_press_delay': 75,
            'min_reaction_time': 115,
            'max_reaction_time': 288,
            'precompute_size': 10000,
        }

        mxw = self.pi_cfg[ 'max_workers' ]
        self.tpexec = ThreadPoolExecutor( max_workers = mxw, thread_name_prefix = 'PxlIntercept' )

        self.app = pxlreact_app

        self.precompute_size = self.pi_cfg[ 'precompute_size' ]
        self.delays = {}

        self._precompute_delays()

    def _precompute_delays( self ):
        """
        Precompute random delays for press (hold) and react (pre-delay).
        """
        def __make_cycle( min_delay, max_delay ):
            values = [ random.randint( min_delay, max_delay ) / 1000
                       for _ in range( self.precompute_size ) ]
            return cycle( values )

        mnp, mxp = self.pi_cfg[ 'min_press_delay' ], self.pi_cfg[ 'max_press_delay' ]
        mnr, mxr = self.pi_cfg[ 'min_reaction_time' ], self.pi_cfg[ 'max_reaction_time' ]

        self.delays = {
            'press': __make_cycle( mnp, mxp ),
            'react': __make_cycle( mnr, mxr ),
        }

    def _next_delay( self, delay_type ):
        """
        Next value from the requested delay cycle; for now assume single-threaded submission.
        """
        return next( self.delays[ delay_type ] )

    def _press( self, key, pre_delay_s, hold_delay_s ):
        if pre_delay_s is not None and pre_delay_s > 0:
            time.sleep( pre_delay_s )

        pyint.key_down( key, delay = hold_delay_s )
        pyint.key_up( key )

    def _press_and_hold( self, key, pre_delay_s, hold_s ):
        if pre_delay_s is not None and pre_delay_s > 0:
            time.sleep( pre_delay_s )

        pyint.key_down( key, delay = hold_s )
        pyint.key_up( key )

    def press( self, key, pre_delay_s = None ):
        hold = self._next_delay( 'press' )
        self.tpexec.submit( self._press, key, pre_delay_s, hold )

    def react( self, key ):
        pre  = self._next_delay( 'react' )
        hold = self._next_delay( 'press' )
        self.tpexec.submit( self._press, key, pre, hold )

    def press_and_hold( self, key, hold_s, pre_delay_s = None ):
        self.tpexec.submit( self._press_and_hold, key, pre_delay_s, hold_s )

    def close( self ):
        print( f'ℹ️ {YELLOW}Closing PxlIntercept...{RESET}' )
        self.tpexec.shutdown( wait = True )


class PxlKbd:

    def __init__( self, pxlintercept ):
        self.pxlintercept = pxlintercept
        self.running = False
        self.context = None

    def __enter__( self ):
        """Context manager entry - start interception"""
        # Create interception context
        self.context = pyint.Interception()
        
        # Set filter to capture only keyboard key down events
        self.context.set_filter( self.context.is_keyboard, FilterKeyFlag.FILTER_KEY_DOWN )


        self.running = True
        print( f'{GREEN}PxlKbd started - listening to keyboard device 2{RESET}' )
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Context manager exit - stop interception"""
        self.running = False
        if self.context:
            self.context.destroy()
        print( f'{YELLOW}PxlKbd stopped{RESET}' )

    def _handle_key_event( self, stroke ):
        """Handle a key press event"""
        scan_code = stroke.code
        flags = stroke.flags
        is_extended = bool( flags & KeyFlag.KEY_E0 )
        
        print( f'{GREEN}Scan Code: {scan_code:3d} | Flags: {flags:02X} | Extended: {is_extended}{RESET}' )
        
        # Exit on escape key (scan code 1)
        if scan_code == 1:
            print( f'{RED}Escape pressed - exiting{RESET}' )
            self.running = False

    def run( self ):
        """Main event loop - capture and process keyboard events"""
        print( f'{CYAN}Press any keys to see scan codes. Keys are BLOCKED from other applications.{RESET}' )
        print( f'{CYAN}Press {YELLOW}ESC{RESET} to exit.{RESET}' )
        
        try:
            while self.running:
                # Wait for input with timeout to allow interruption
                device = self.context.await_input( timeout_milliseconds = 100 )
                if device is None:
                    continue  # No event, continue loop

                print( f'{CYAN}Event from Device: {device}{RESET}' )
                
                # Receive the stroke from the device
                stroke = self.context.devices[device].receive()
                if stroke is None:
                    continue
                
                # Check if it's a keyboard stroke with key down
                if isinstance( stroke, pyint.KeyStroke ) and stroke.flags == KeyFlag.KEY_DOWN:
                    # Handle the key event
                    self._handle_key_event( stroke )
                    
                    # BLOCK the key from reaching other applications
                    # Only pass through if it's the escape key (scan code 1)
                    if stroke.code == 1:
                        # Allow escape to pass through for exit
                        self.context.send( device, stroke )
                    else:
                        # Block all other keys - don't send them back
                        pass
                else:
                    # Pass through non-key-down events
                    self.context.send( device, stroke )
                    
        except KeyboardInterrupt:
            print( f'{YELLOW}Interrupted by user{RESET}' )
        except Exception as e:
            print( f'{RED}Error in PxlKbd run loop: {e}{RESET}' )



def main():
    """Keyboard scan code viewer"""
    print( f'{GREEN}=== Keyboard Scan Code Viewer ==={RESET}' )
    print( f'{CYAN}Press any keys to see their scan codes.{RESET}' )
    print( f'{CYAN}Press {YELLOW}ESC{RESET} to exit.' )
    print()
    
    # Create PxlIntercept instance
    pxlintercept = PxlIntercept( None )  # No app reference needed for testing
    
    # Create and run PxlKbd with context manager
    with PxlKbd( pxlintercept ) as pxlkbd:
        pxlkbd.run()
    
    # Clean up
    pxlintercept.close()
    print( f'{GREEN}Scan code viewer completed{RESET}' )

if __name__ == '__main__':
    main()
