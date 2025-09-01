import random
import time
from itertools import cycle

from concurrent.futures import ThreadPoolExecutor

"""
pyinterception interacts with the interception driver.

Local & online references:
    - pyinterception_README.md
    - pyinterception_inputs.py
    - pyinterception.py
    - https://github.com/kennyhml/pyinterception
    - https://github.com/oblitum/Interception
"""
import interception as pyint

# ANSI colors and RESET for highlighting Terminal output
from ansi import *

# Force keyboard to 0 (sometimes pyint picks a different ID); environment is stable no need to config
pyint.set_devices( keyboard = 0 )


class PxlIntercept:

    """
    PxlIntercept encapsulates interactions with python-interception to send key events to applications
    and game clients that are received as if delivered from hardware.

    PxlIntercept uses asynchronous, non-blocking calls with the intent of supporting common use
    cases like "pressing one key while holding another" which are typical in games. 
    """

    def __init__( self, pxlreact_app ):

        self.pi_cfg = {
            'max_workers': 3,
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

    """
    PxlKbd has two functions within the PxlReact application:

        1) Manage keybinding (aka remapping) for the project; respond to assigned keys by dispatching
            actions via PxlIntercept.

        2) Interact with pyinterception and the interception driver to "capture" keyboard events and
            respond accordingly; the 'starter kit' of responses to key events is:
            2.1) do nothing: keys which have no explicit assignment should simply be "passed on" so
                they are received by applications unmodified
            2.2) do something else: building on the methods in PxlIntercept, this class will remap
                or "transform" some keys into different actions or sequences of actions the simplest
                example being simply sending a different key (e.g., when the user presses 'f' applications
                see 'r' instead).

    When remapping/transforming keys, the class will need two modes of operation: one which "swallows"
    the original key and only performs the remapped actions, and another which passes the original
    key along with performing the remapped action. Examples of this:

        - blocked/swallowed => the user presses 'f' and the application sees 'r' only and nothing else

        - passed through => the user presses 'f' and the application sees 'r' and 'f' both (in the default
        case it will not be important to guarantee any particular order of these events, though ideally
        when passing through the original key should be prioritized over the "triggered" action).

    """

    def __init__( self ):
        pass
