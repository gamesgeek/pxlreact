"""
ACTIONS can become a part of a ROTATION; ACTIONS are defined by properties.

`key` may be a keyboard key (e.g. "e") or a mouse button: "left", "right", "middle" (clicks at
the current cursor position).
"""
ACTIONS = {
    "deception": {
        "key": "left",
        "cooldown": 0,
        "cast_time": 0.3,
        "color_check": {
            "px": 2082,
            "py": 1276,
            "color": (105, 84, 71)
        },
    },
    "brutality": {
        "key": "right",
        "cooldown": 0,
        "cast_time": 0.3,
        "color_check": {
            "px": 2217,
            "py": 1285,
            "color": (85, 62, 42)
        },
    },
    "first_volcano": {
        "key": "q",
        "cooldown": 5.4,
        "cast_time": 0.65,
        "color_check": {},
    },
    "second_volcano": {
        "key": "q",
        "cooldown": 5.4,
        "cast_time": 0.65,
        "color_check": {},
    },
    "ele weakness": {
        "key": "e",
        "cooldown": 12,
        "cast_time": 0.6,
        "color_check": {},
    },
    # (2074, 1399) - (113, 113, 101)
    "pain offering": {
        "key": "r",
        "cooldown": 6,
        "cast_time": 0.6,
        "color_check": {
            "px": 2074,
            "py": 1399,
            "color": (113, 113, 101)
        },
    }
}

# ROTATIONS are sequences of ACTIONS
ROTATIONS = {
    "volcano": ["first_volcano", "second_volcano"],
    "main": ["deception", "brutality"],
    "boss": ["ele weakness", "pain offering"]
}

# REMAPS bind keys to ROTATIONS
REMAPS = {
    "m": "volcano",
    "l": "main",
    "z": "boss",
}
