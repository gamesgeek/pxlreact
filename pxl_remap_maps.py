"""
ACTIONS can become a part of a ROTATION; ACTIONS are defined by properties.

`key` may be a keyboard key (e.g. "e") or a mouse button: "left", "right", "middle" (clicks at
the current cursor position).

`color_check` is a list of conditions that must ALL hold for the action to fire (logical AND).
Each condition is a dict:
    { "px": int, "py": int, "color": (r, g, b), "match": bool }
`match` defaults to True ("the pixel must be this color"); set `match`: False to require that the
pixel is NOT this color. An omitted or empty `color_check` means no color gate. A single condition
may be written as a bare dict instead of a one-element list.
"""
ACTIONS = {
    # (2138, 1277) - (160, 187, 250)
    "death storm": {
        "key": "middle",
        "cooldown": 3,
        "cast_time": 1.5,
        "color_check": [
            { "px": 2138, "py": 1277, "color": (160, 187, 250) },
        ],
    },
    # (2149, 1363) - (108, 178, 197)
    # Shield = (254, 1198) - (165, 227, 240)
    # Shield = (165, 1235) - (127, 180, 190)
    # "navira's well": {
    #     "key": "f",
    #     "cooldown": 4.76,
    #     "cast_time": 0,
    #     "color_check": [
    #         { "px": 2194, "py": 1392, "color": (79, 227, 243) },
    #         { "px": 254, "py": 1198, "color": (165, 227, 240), "match": False },
    #         { "px": 165, "py": 1235, "color": (127, 180, 190), "match": False },
    #     ],
    # },
    # (1938, 1368) - (241, 79, 40)
    "ruzhan's trap": {
        "key": "q",
        "cooldown": 4.04,
        "cast_time": 0.28,
        "color_check": [
            { "px": 1938, "py": 1368, "color": (241, 79, 40) },
        ],
    },
    # (1945, 1371) - (184, 165, 133)
    "ruzhan's reckoning": {
        "key": "q",
        "cooldown": 5,
        "cast_time": 0.28,
        "color_check": [
            { "px": 1945, "py": 1371, "color": (184, 165, 133) },
        ],
    },
    "deception1": {
        "key": "left",
        "cooldown": 1.2,
        "cast_time": 0.28,
        "color_check": [
            { "px": 2082, "py": 1276, "color": (105, 84, 71) },
        ],
    },
    "deception2": {
        "key": "left",
        "cooldown": 1.2,
        "cast_time": 0.28,
        "color_check": [
            { "px": 2082, "py": 1276, "color": (105, 84, 71) },
        ],
    },
    "brutality": {
        "key": "right",
        "cooldown": 0,
        "cast_time": 0.28,
        "color_check": [
            { "px": 2217, "py": 1285, "color": (85, 62, 42) },
        ],
    },
    "unholy might": {
        "key": "right",
        "cooldown": 15,
        "cast_time": 0.28,
        "color_check": [
            { "px": 2217, "py": 1285, "color": (85, 62, 42) },
        ],
    },
    "ele weakness": {
        "key": "e",
        "cooldown": 12,
        "cast_time": 0.65,
        "color_check": [],
    },
    "despair1": {
        "key": "e",
        "cooldown": 8,
        "cast_time": 0.5,
        "color_check": [],
    },
    "despair2": {
        "key": "e",
        "cooldown": 8,
        "cast_time": 0.5,
        "color_check": [],
    },
    "pain offering": {
        "key": "r",
        "cooldown": 8,
        "cast_time": 0.6,
        "color_check": [
            { "px": 2074, "py": 1399, "color": (113, 113, 101) },
        ],
    },
}

# ROTATIONS are sequences of ACTIONS
ROTATIONS = {
    "main": ["unholy might", "ruzhan's trap", "deception1", "deception2", "brutality"],
    "boss": ["despair1", "pain offering", "despair2"]
}

# REMAPS bind keys to ROTATIONS
REMAPS = {
    "l": "main",
    "z": "boss",
}
