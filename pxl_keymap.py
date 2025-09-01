from interception import _keycodes as kc
from pxl_lib import read_json, write_json

SCAN_CODES = read_json( "./dat/scancodes.json" )
KEY_NAMES = {}

# KEY_NAMES is a "reverse" dictionary to lookup key names by scan code
for k, v in SCAN_CODES.items():
    KEY_NAMES[ v ] = k
