"""
pxl_config.py loads, normalizes, and validates the two external configuration files:

- settings.toml: low-churn application settings edited manually (devices, timing, defaults)
- profile.json: gameplay configuration (reactions, actions, rotations, wincheck), managed by
  the pxl_editor GUI or edited manually

Normalization happens entirely at load time so runtime code never consults global defaults:
colors become tuples and every color check carries an explicit `tolerance` (falling back to
color.default_tolerance from settings; wincheck markers default to 0 = exact match).
"""

import json
import tomllib

from ansi import *

SETTINGS_PATH = "settings.toml"
PROFILE_PATH = "profile.json"

REACTION_TYPES = ( "react_if_color", "react_if_not_color" )


class ConfigError( ValueError ):
    """Raised when a configuration file is missing, malformed, or fails validation."""


def _fail( message ):
    print( f"{RED}Config error: {message}{RESET}" )
    raise ConfigError( message )


_settings = None


def get_settings( path = SETTINGS_PATH ):
    """Load, normalize, and cache settings.toml; subsequent calls return the cached dict."""
    global _settings
    if _settings is None:
        _settings = _load_settings( path )
    return _settings


def _load_settings( path ):
    try:
        with open( path, "rb" ) as fh:
            raw = tomllib.load( fh )
    except OSError as exc:
        _fail( f"cannot read {path} ({exc})" )
    except tomllib.TOMLDecodeError as exc:
        _fail( f"invalid TOML in {path} ({exc})" )

    for section in ( "app", "color", "devices", "intercept", "remapper", "gui", "trigger_log",
                     "capture" ):
        if section not in raw:
            _fail( f"{path}: missing [{section}] section" )

    tick = raw[ "app" ].get( "tick_interval", 0.025 )
    if not ( 0 < tick < 1 ):
        _fail( f"{path}: unreasonable app.tick_interval: {tick}" )

    raw[ "app" ].setdefault( "frame_max_age", 0.010 )
    if not ( 0 < raw[ "app" ][ "frame_max_age" ] <= tick ):
        _fail( f"{path}: app.frame_max_age must be positive and no larger than tick_interval" )

    tolerance = raw[ "color" ].get( "default_tolerance" )
    if not ( isinstance( tolerance, int ) and tolerance >= 0 ):
        _fail( f"{path}: color.default_tolerance must be a non-negative integer" )

    for key in ( "keyboard_hwid", "mouse_hwid" ):
        if not raw[ "devices" ].get( key ):
            _fail( f"{path}: devices.{key} is required" )

    # Trigger log: empty path disables persistence; collapse tolerance defaults to the color default
    tlog = raw[ "trigger_log" ]
    tlog[ "path" ] = tlog.get( "path" ) or None
    tlog.setdefault( "collapse_tolerance", tolerance )

    gui = raw[ "gui" ]
    gui.setdefault( "statusbar_enabled", True )
    gui.setdefault( "fps", 15 )
    gui.setdefault( "color_check_hz", 3 )
    gui.setdefault( "pos", [ 20, 20 ] )
    gui.setdefault( "size", [ 460, 480 ] )
    gui.setdefault( "reload_key", "r" )
    if not ( 0 < gui[ "fps" ] <= 60 ) or not ( 0 < gui[ "color_check_hz" ] <= gui[ "fps" ] ):
        _fail( f"{path}: gui.fps / gui.color_check_hz out of range" )

    return raw


def load_profile( path = PROFILE_PATH, default_tolerance = None ):
    """
    Load, normalize, and validate profile.json. Returns a dict with keys `wincheck`, `reactions`,
    `actions`, `rotations`. Colors are tuples and every color check carries an explicit
    `tolerance` after this call.
    """
    if default_tolerance is None:
        default_tolerance = get_settings()[ "color" ][ "default_tolerance" ]

    try:
        with open( path, "r", encoding = "utf-8" ) as fh:
            raw = json.load( fh )
    except OSError as exc:
        _fail( f"cannot read {path} ({exc})" )
    except ValueError as exc:
        _fail( f"invalid JSON in {path} ({exc})" )

    for section in ( "wincheck", "reactions", "actions", "rotations" ):
        if section not in raw:
            _fail( f"{path}: missing '{section}' section" )

    profile = {
        "wincheck": _normalize_wincheck( raw[ "wincheck" ] ),
        "reactions": { name: _normalize_reaction( name, data, default_tolerance )
                       for name, data in raw[ "reactions" ].items() },
        "actions": { name: _normalize_action( name, data, default_tolerance )
                     for name, data in raw[ "actions" ].items() },
        "rotations": { name: _normalize_rotation( name, data )
                       for name, data in raw[ "rotations" ].items() },
    }

    # Referential integrity: rotations name real actions; source keys are unique across rotations
    keys_seen = {}
    for rname, cfg in profile[ "rotations" ].items():
        if cfg[ "key" ] in keys_seen:
            _fail( f"rotations '{keys_seen[ cfg[ 'key' ] ]}' and '{rname}' share key '{cfg[ 'key' ]}'" )
        keys_seen[ cfg[ "key" ] ] = rname
        for aname in cfg[ "actions" ]:
            if aname not in profile[ "actions" ]:
                _fail( f"rotation '{rname}' references unknown action '{aname}'" )

    return profile


def profile_points( profile ):
    """
    Every screen coordinate a normalized profile can read at runtime: wincheck markers, enabled
    reactions (monitored pixel + color-readiness pixels), and action color checks. Used to size
    the shared PixelSource frame-cache region.
    """
    points = [ ( m[ 'x' ], m[ 'y' ] ) for m in profile[ 'wincheck' ][ 'markers' ] ]
    for data in profile[ 'reactions' ].values():
        if not data[ 'enabled' ]:
            continue
        points.append( ( data[ 'x' ], data[ 'y' ] ) )
        for spec in ( data[ 'ready' ] or [] ):
            if spec[ 'type' ] == 'color':
                points.append( ( spec[ 'px' ], spec[ 'py' ] ) )
    for action in profile[ 'actions' ].values():
        for cc in action[ 'color_check' ]:
            points.append( ( cc[ 'px' ], cc[ 'py' ] ) )
    return points


def _color_tuple( value, owner ):
    """Validate an RGB triple (JSON list) and return it as a tuple."""
    if not ( isinstance( value, ( list, tuple ) ) and len( value ) == 3
             and all( isinstance( c, int ) and 0 <= c <= 255 for c in value ) ):
        _fail( f"invalid color for {owner}: {value}" )
    return tuple( value )


def _check_coords( x, y, owner ):
    if not ( isinstance( x, int ) and -2560 <= x < 2560 ):
        _fail( f"invalid x for {owner}: {x}" )
    if not ( isinstance( y, int ) and 0 <= y < 1440 ):
        _fail( f"invalid y for {owner}: {y}" )


def _check_tolerance( value, owner ):
    if not ( isinstance( value, int ) and value >= 0 ):
        _fail( f"invalid tolerance for {owner}: {value}" )
    return value


def _normalize_wincheck( data ):
    target = data.get( "target_window" )
    if not ( isinstance( target, str ) and target ):
        _fail( "wincheck.target_window must be a non-empty string" )

    markers = data.get( "markers" )
    if not ( isinstance( markers, list ) and markers ):
        _fail( "wincheck.markers must be a non-empty list" )

    normalized = []
    for i, m in enumerate( markers ):
        owner = f"wincheck marker {i}"
        x, y = m.get( "x" ), m.get( "y" )
        _check_coords( x, y, owner )
        normalized.append( {
            "x": x,
            "y": y,
            "color": _color_tuple( m.get( "color" ), owner ),
            # Markers guard against inadvertent reactions, so they default to exact match
            "tolerance": _check_tolerance( m.get( "tolerance", 0 ), owner ),
        } )

    return { "target_window": target, "markers": normalized }


def _normalize_ready_spec( spec, owner, default_tolerance ):
    rtype = spec.get( "type", "cooldown" )
    if rtype == "color":
        _check_coords( spec.get( "px", 0 ), spec.get( "py", 0 ), owner )
        lockout = spec.get( "lockout", 0.5 )
        if not ( 0 <= lockout < 10 ):
            _fail( f"unreasonable ready lockout for {owner}: {lockout}" )
        return {
            "type": "color",
            "px": spec[ "px" ],
            "py": spec[ "py" ],
            "color": _color_tuple( spec.get( "color" ), owner ),
            "tolerance": _check_tolerance( spec.get( "tolerance", default_tolerance ), owner ),
            "lockout": lockout,
        }
    if rtype == "cooldown":
        cd = spec.get( "cooldown", 0 )
        if not ( 0 < cd < 180 ):
            _fail( f"unreasonable ready cooldown for {owner}: {cd}" )
        return { "type": "cooldown", "cooldown": cd }
    _fail( f"unknown ready type for {owner}: {rtype}" )


def _normalize_reaction( name, data, default_tolerance ):
    owner = f"reaction '{name}'"
    _check_coords( data.get( "x", 0 ), data.get( "y", 0 ), owner )

    if data.get( "type" ) not in REACTION_TYPES:
        _fail( f"invalid type for {owner}: {data.get( 'type' )}" )

    press = data.get( "press" )
    if not ( isinstance( press, str ) and press ):
        _fail( f"{owner} must define a non-empty 'press' key" )

    confirm = data.get( "confirm", 0.0 )
    if not ( 0 <= confirm < 2 ):
        _fail( f"unreasonable confirm for {owner}: {confirm}" )

    cast_time = data.get( "cast_time", 0.0 )
    if not ( 0 <= cast_time < 10 ):
        _fail( f"unreasonable cast_time for {owner}: {cast_time}" )

    ready = data.get( "ready" )
    if ready is not None:
        specs = ready if isinstance( ready, list ) else [ ready ]
        ready = [ _normalize_ready_spec( s, owner, default_tolerance ) for s in specs ]
    else:
        cooldown = data.get( "cooldown", 0 )
        if not ( 0 < cooldown < 180 ):  # avoid ms/s confusion (never > 3 minutes)
            _fail( f"unreasonable cooldown for {owner}: {cooldown}" )

    ignore = data.get( "ignore_colors", [] )
    if not isinstance( ignore, list ):
        _fail( f"ignore_colors for {owner} must be a list" )

    return {
        "enabled": bool( data.get( "enabled", True ) ),
        "x": data[ "x" ],
        "y": data[ "y" ],
        "type": data[ "type" ],
        "color": _color_tuple( data.get( "color" ), owner ),
        "tolerance": _check_tolerance( data.get( "tolerance", default_tolerance ), owner ),
        "confirm": confirm,
        "cooldown": data.get( "cooldown" ),
        "ready": ready,
        "cast_time": cast_time,
        "ignore_colors": [ _color_tuple( c, owner ) for c in ignore ],
        "press": press,
    }


def _normalize_rotation( name, data ):
    """A rotation binds its own source key to an ordered action sequence (remaps tier retired)."""
    owner = f"rotation '{name}'"
    if not isinstance( data, dict ):
        _fail( f"{owner} must be an object with 'key' and 'actions'" )

    key = data.get( "key" )
    if not ( isinstance( key, str ) and key ):
        _fail( f"{owner} must define a non-empty source 'key'" )

    actions = data.get( "actions" )
    if not ( isinstance( actions, list ) and actions ):
        _fail( f"{owner} must list at least one action" )

    return { "key": key, "actions": list( actions ) }


def _normalize_action( name, data, default_tolerance ):
    owner = f"action '{name}'"

    key = data.get( "key" )
    if not ( isinstance( key, str ) and key ):
        _fail( f"{owner} must define a non-empty 'key'" )

    cooldown = data.get( "cooldown", 0.0 )
    if not ( 0 <= cooldown < 180 ):
        _fail( f"unreasonable cooldown for {owner}: {cooldown}" )

    cast_time = data.get( "cast_time", 0.0 )
    if not ( 0 <= cast_time < 10 ):
        _fail( f"unreasonable cast_time for {owner}: {cast_time}" )

    checks = data.get( "color_check" ) or []
    if isinstance( checks, dict ):
        checks = [ checks ]
    normalized = []
    for i, cc in enumerate( checks ):
        cowner = f"{owner} color_check {i}"
        _check_coords( cc.get( "px", 0 ), cc.get( "py", 0 ), cowner )
        normalized.append( {
            "px": cc[ "px" ],
            "py": cc[ "py" ],
            "color": _color_tuple( cc.get( "color" ), cowner ),
            "match": bool( cc.get( "match", True ) ),
            "tolerance": _check_tolerance( cc.get( "tolerance", default_tolerance ), cowner ),
        } )

    return {
        "key": key,
        "cooldown": cooldown,
        "cast_time": cast_time,
        "color_check": normalized,
    }
