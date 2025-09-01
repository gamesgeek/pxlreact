"""
These hardware IDs and handles are taken from a third party tool; pyinterception should be capable of detecting these
automatically, but we can use this data to verify that it has correctly identified each device.
"""
MY_DEVICES = {
    "unknown_device": {
        "id": 1,
        "vid": 0x046D,
        "pid": 0xC08B,
        "handle": "HID\\VID_046D&PID_C08B&REV_2703&MI_01&Col01",
        "name": "pyinterception sends events from this device ??",
    },
    "standard_keyboard": {
        "id": 2,
        "vid": 0x046D,
        "pid": 0xC33F,
        "handle": "HID\\VID_046D&PID_C33F&REV_3100&MI_00",
        "name": "Logitech G815",
    },
    "unknown_device": {
        "id": 3,
        "vid:": 0x046D,
        "pid": 0xC33F,
        "handle": "HID\\VID_046D&PID_C33F&REV_3100&MI_01&Col01",
        "name": "pyinterception sends events from this device ??",
    },
    "extended_keyboard": {
        "id": 4,
        "vid": 0x046D,
        "pid": 0xC232,
        "handle": "HID\\VID_046D&PID_C232",
        "name": "Logitech G815 Extended",
    },
    "mouse": {
        "id": 11,
        "vid": 0x046D,
        "pid": 0xC08B,
        "handle": "HID\\VID_046D&PID_C08B&REV_2703&MI_00",
        "name": "Logitech G502",
    }
}
