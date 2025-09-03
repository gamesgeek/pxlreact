import random
import time
from itertools import cycle

from concurrent.futures import ThreadPoolExecutor

# Using local pyinterception files for better control and stability
import pyinterception.src.interception as pyint
from pyinterception.src.interception.constants import FilterKeyFlag, KeyFlag

from ansi import *
from pxl_keys import DEVICES

# Import maps for key names and codes e.g., KEY_CODES[ 'esc' ] = 0x1 and KEY_NAMES[ 0x1 ] = 'esc'
from pxl_keys import KEY_CODES, KEY_NAMES

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

pi = pyint.Interception()

# Find our keyboard within the devices list
my_hwid = DEVICES['keyboard']['handle']
idx = 0
for device in pi.devices:
    hwid = device.get_HWID()
    if hwid is not None and my_hwid in hwid:
         pyint.set_devices( keyboard = idx )
         break
    idx += 1

# Begin capturing keyboard events (reports to terminal w/ device ID & code)
pyint.capture_keyboard()
