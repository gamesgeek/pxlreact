# PxlReact (Headless/Core)

PxlReact is a lightweight, headless automation utility for Windows that:
- Monitors specific screen pixels for color changes
- Triggers predefined reactions (keyboard events via Interception) when changes are detected

The project intentionally avoids UI complexity and runs without a GUI. It focuses on responsiveness, clarity, and easy customization in code.

---

## Core Modules (Headless)

- `pxlreactHL.py`
  - Main entry point. Starts a polling loop and wires hotkeys.
  - Creates `PxlReactApp`, preloads reactions from `PxlReactionRegistry`, and polls assigned pixels.
  - Hotkeys: `F12` to exit.

- `pxl_lib.py`
  - Utilities for reading screen pixels, color comparison with tolerance, mouse position, and searching a region for the closest color.
  - Key helpers: `get_pixel_color`, `colors_different`, `get_mouse_pos`, `find_most_similar_pixel`.

- `pxl_winwatch.py` (session gating)
  - Maintains an `active` flag so reactions only fire in the intended context.
  - Checks the foreground window title and validates a marker pixel’s color.
  - Defaults target to `Path of Exile 2` and a specific marker coordinate/color.

- `pxl_intercept.py` (hardware-like key events)
  - Sends key events using a local clone of `pyinterception` (Interception wrapper).
  - Adds randomized pre-delays and key-hold durations to simulate human-like input.
  - Non-blocking via `ThreadPoolExecutor` to support overlapping actions.

- In-code data model
  - `Pxl`: a monitored pixel; maintains its latest RGB and optional reaction.
  - `PxlReaction`: trigger logic + cooldown + function to execute when conditions are met.
  - `PxlReactionRegistry`: predefined reactions (coordinates, colors, cooldowns, and functions).

---

## Quick Start (Windows + PowerShell)

- Requirements:
  - Windows 11
  - Python 3.12.10
  - Local clone of this repository
  - Interception driver (see links below)

- Create/activate the project venv (stored in `./.pxlenv`):

```powershell
cd C:\dev\pxlreact
python -m venv .pxlenv
.\.pxlenv\Scripts\Activate.ps1
```

- Install Python deps used by the headless core:

```powershell
pip install keyboard pywin32
```

Notes:
- `pyinterception` is vendored in `pyinterception/` and imported directly from source; no pip install needed for it.
- Do not modify anything under `pyinterception/` unless explicitly intended.

---

## Run

```powershell
python pxlreactHL.py
```

- Press `F12` to exit cleanly.
- Reactions only trigger when `pxl_winwatch.PxlWinWatch.active` is `True` (foreground window and marker color match).

---

## How It Works (at a glance)

- The app creates a small set of `Pxl` instances and assigns reactions from `PxlReactionRegistry`.
- A polling loop (default ~25 ms) updates each pixel’s RGB via `get_pixel_color`.
- When a pixel’s color differs enough from its configured reference color (with tolerance and ignored deltas), its reaction may trigger.
- `pxl_intercept.PxlIntercept` executes the mapped key press with random pre-delay and hold durations.

Default behavior (example registry):
- Two reactions are preloaded (e.g., `HP1`, `MP1`) with hard-coded screen coordinates and RGB colors.
- When off-color (or color-changed) is detected, they simulate pressing keys like `1` or `2` with a defined cooldown.

---

## Configuration

- Session gating (window + marker): `pxl_winwatch.py`
  - `target_app`, `marker_x`, `marker_y`, `marker_color`

- Reactions and pixels: `pxlreactHL.py` and `PxlReactionRegistry`
  - Edit registry entries (coordinates, colors, cooldowns, and `reaction` function).
  - Adjust `PxlReactApp.pixel_count`, `tick_interval`, and initial pixel assignments as needed.

- Interception timing (randomized delays): `pxl_intercept.py`
  - `min_press_delay`, `max_press_delay`, `min_reaction_time`, `max_reaction_time`, `max_workers`.

---

## Notes & Limitations

- Headless-only: there is no GUI.
- This utility is tailored for a Windows desktop workflow and a specific app profile by default.
- Color-based triggers can be sensitive to overlays, post-processing, and gamma changes—adjust tolerance/markers if needed.

---

## References

- `pyinterception` (local clone in this repo)
  - `https://github.com/kennyhml/pyinterception`
- Interception driver
  - `https://github.com/oblitum/Interception#readme`
- Python
  - `https://www.python.org/`

---

## Repository Layout (excerpt)

```
c:\dev\pxlreact\
  pxlreactHL.py         # headless main app
  pxl_winwatch.py       # session gating (window title + marker pixel)
  pxl_lib.py            # pixel/color utilities
  pxl_intercept.py      # interception-based keyboard events
  ansi.py               # simple ANSI color helpers for console output
  pyinterception/       # local clone of third-party library (do not modify)
```
