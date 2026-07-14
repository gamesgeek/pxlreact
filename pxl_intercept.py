import random
import time
from itertools import cycle

from concurrent.futures import ThreadPoolExecutor

from ansi import *

from pxl_config import get_settings

# Using local pyinterception files for better control and stability
import pyinterception.src.interception as pyint


def detect_device_index( my_hwid ):
    """
    Find the interception device index whose HWID contains `my_hwid`, using a short-lived probe
    context. Returns the index, or None if no match is found (callers should fall back to the
    library/context default). Shared with PxlRemapper's capture-context setup.
    """
    probe = pyint.Interception()
    try:
        idx = 0
        for device in probe.devices:
            hwid = device.get_HWID()
            if hwid is not None and my_hwid in hwid:
                return idx
            idx += 1
    finally:
        probe.destroy()
    return None


# Point the library's default send context at our keyboard
_idx = detect_device_index( get_settings()[ 'devices' ][ 'keyboard_hwid' ] )
if _idx is not None:
    pyint.set_devices( keyboard = _idx )


class PxlIntercept:

    """
    PxlIntercept encapsulates interactions with python-interception to send key events to applications
    and game clients that are received as if delivered from hardware.

    PxlIntercept uses asynchronous, non-blocking calls with the intent of supporting common use
    cases like "pressing one key while holding another" which are typical in games. 
    """

    def __init__( self ):

        # Injection thread pool size and humanized delay ranges (ms), from settings.toml
        self.pi_cfg = get_settings()[ 'intercept' ]

        mxw = self.pi_cfg[ 'max_workers' ]
        self.tpexec = ThreadPoolExecutor( max_workers = mxw, thread_name_prefix = 'PxlIntercept' )

        self.precompute_size = self.pi_cfg[ 'precompute_size' ]
        self.delays = {}

        self._precompute_delays()

    def _precompute_delays( self ):
        """
        Precompute random hold delays for press.
        """
        def __make_cycle( min_delay, max_delay ):
            values = [ random.randint( min_delay, max_delay ) / 1000
                       for _ in range( self.precompute_size ) ]
            return cycle( values )

        mnp, mxp = self.pi_cfg[ 'min_press_delay' ], self.pi_cfg[ 'max_press_delay' ]

        self.delays = {
            'press': __make_cycle( mnp, mxp ),
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

    def press( self, key, pre_delay_s = None ):
        hold = self._next_delay( 'press' )
        self.tpexec.submit( self._press, key, pre_delay_s, hold )

    def close( self ):
        print( f'ℹ️ {YELLOW}Closing PxlIntercept...{RESET}' )
        self.tpexec.shutdown( wait = True )
