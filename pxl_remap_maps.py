"""
ACTIONS can become a part of a ROTATION; ACTIONS are defined by properties:
"""
ACTIONS = {
    # (2012, 1367) - (85, 64, 44)
    "brutality": {
        "key": "e",
        "cooldown": 0,
        "cast_time": 0.27,
        "color_check": {
            "px": 2012,
            "py": 1367,
            "color": (85, 64, 44)
        },
    },
    # (2087, 1374) - (103, 85, 76)
    "deception": {
        "key": "r",
        "cooldown": 0,
        "cast_time": 0.27,
        "color_check": {
            "px": 2087,
            "py": 1374,
            "color": (103, 85, 76)
        },
    },
    # (2198, 1367) - (187, 121, 31)
    "demise": {
        "key": "f",
        "cooldown": 0,
        "cast_time": 0.44,
        "color_check": {
            "px": 2198,
            "py": 1367,
            "color": (187, 121, 31)
        },
    },
    # (2217, 1374) - (32, 103, 57)
    "gas arrow": {
        "key": "f",
        "cooldown": 0,
        "cast_time": 0,
        "color_check": {
            "px": 2217,
            "py": 1374,
            "color": (32, 103, 57)
        },
    },
    "volcano": {
        "key": "q",
        "cooldown": 8.49,
        "cast_time": 0.49,
        "color_check": {},
    },
    "ele weakness": {
        "key": "t",
        "cooldown": 7.82,
        "cast_time": 0.47,
        "color_check": {},
    },
    # (2069, 1368) - (234, 107, 42)
    "ruz's brand": {
        "key": "r",
        "cooldown": 0,
        "cast_time": 0.29,
        "color_check": {
            "px": 2069,
            "py": 1368,
            "color": (234, 107, 42)
        },
    },
}

# ROTATIONS are sequences of ACTIONS
ROTATIONS = {
    "quick": ["brutality"],
    "main": ["ele weakness", "volcano", "brutality", "demise"]
}

# REMAPS bind keys to ROTATIONS
REMAPS = {
    "m": "quick",
    "l": "main",
}
