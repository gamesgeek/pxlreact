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
  - Hotkeys: `F12` (or `ESC`) to exit; `Ctrl+P` toggles a single-pixel monitor that reports the color under the cursor when it changes (useful for capturing reference / `ignore_colors` RGB values).

- `pxl_lib.py`
  - Utilities for reading screen pixels, color comparison with tolerance, mouse position, and searching a region for the closest color.
  - Key helpers: `get_pixel_color`, `colors_different`, `colors_similar`, `matches_any`, `get_mouse_pos`, `find_most_similar_pixel`.
  - `ColorCondition`: a reusable "pixel (px, py) must match / must not match `color`" test used to compose multi-layered color checks (see remapping config below).

- `pxl_wincheck.py` (session gating)
  - Exposes an on-demand `check()` so reactions only fire in the intended context.
  - Reads the foreground window title and validates a marker pixel’s color live at each call.
  - Defaults target to `Path of Exile 2` and a specific marker coordinate/color.

- `pxl_intercept.py` (hardware-like key events)
  - Sends key events using a local clone of `pyinterception` (Interception wrapper).
  - Adds randomized pre-delays and key-hold durations to simulate human-like input.
  - Non-blocking via `ThreadPoolExecutor` to support overlapping actions.

- In-code data model
  - `Pxl`: a monitored pixel; maintains its latest RGB and optional reaction.
  - `PxlReaction`: trigger logic + a readiness strategy + function to execute when conditions are met. Two trigger types: `react_if_not_color` (fire when the pixel deviates from the reference color) and `react_if_color` (fire when it matches). For `react_if_not_color`, an optional `ignore_colors` list names benign off-colors (e.g. poison/curse orb tints) that must not trigger. Readiness is pluggable: `CooldownReadiness` (time elapsed) or `ColorReadiness` (an availability indicator pixel shows the expected color) - see Configuration.
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
- Optional: `pip install mss` is only needed if you enable the capture debug mode (see Configuration).

---

## Run

```powershell
python pxlreactHL.py
```

- Press `F12` to exit cleanly.
- Reactions only trigger when `pxl_wincheck.PxlWinCheck.check()` returns `True` (foreground window and marker color match).

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

- Session gating (window + marker): `pxl_wincheck.py`
  - `target_app`, `marker_x`, `marker_y`, `marker_color`

- Reactions and pixels: `pxlreactHL.py` and `PxlReactionRegistry`
  - Edit registry entries (coordinates, colors, readiness, and `reaction` function).
  - `type`: `react_if_not_color` or `react_if_color`. This is the firing *condition* and is independent of readiness.
  - Readiness (when the reaction is *allowed* to fire) is a pluggable strategy:
    - Time-based (default): set `cooldown` (seconds), or `'ready': {'type': 'cooldown', 'cooldown': N}`. Best for fixed-recharge abilities (flasks).
    - Color-based: `'ready': {'type': 'color', 'px': X, 'py': Y, 'color': (r,g,b), 'lockout': 0.5}`. The reaction is ready only while the indicator pixel shows `color` - use for emergency abilities whose cooldown is too variable to time. `lockout` (default 0.5 s) briefly suppresses re-firing right after a press while the icon updates.
    - Combined: set `ready` to a **list** of specs that must all hold (AND). Example (CV1): a 6 s minimum cooldown AND the skill icon showing available - `'ready': [{'type':'cooldown','cooldown':6}, {'type':'color','px':2153,'py':1384,'color':(71,204,237)}]`.
  - `cast_time` (optional, seconds): when a reaction fires an action that takes time to cast, set `cast_time` so a shared cast lock is armed on firing. While the lock is active the keyboard remapper drops remapped keypresses so they cannot interrupt the cast. Reactions and remap actions (`pxl_remap_maps.py` `cast_time`) share the same lock. Example: CV1 uses `'cast_time': 0.4`.
  - `ignore_colors` (optional, `react_if_not_color`): a list of RGB tuples for sustained-but-benign off-colors that should not trigger. A reading similar to any entry is treated as on-color. Capture tinted-orb RGBs with the `Ctrl+P` pixel monitor, or read them off the trigger-log report (below).
  - Adjust `PxlReactApp.pixel_count`, `tick_interval`, and initial pixel assignments as needed.

- Trigger log (discover ignorable colors): `PxlReactionRegistry`
  - `trigger_log_enabled` (default `True`): record the pixel color that caused each reaction firing.
  - `trigger_log_verbose` (default `False`): also echo a color swatch on every trigger (noisy).
  - `trigger_log_collapse_tolerance` (default `COLOR_TOLERANCE`): SSD threshold for merging near-identical colors in the report.
  - `trigger_log_path` (default `trigger_log.json`): JSON file the tally persists to. Set to `None` to keep counts in memory only.
  - `trigger_log_save_interval` (default `60.0` s): how often the file is rewritten during play (it is also written on exit).
  - Persistence: counts accumulate **across sessions**. On startup the existing JSON is loaded and merged; during play the file is rewritten every `trigger_log_save_interval` seconds and once more (forced) at exit, using an atomic temp-file replace so a crash cannot corrupt the data. The on-disk shape is `{ "REACTION": { "r,g,b": count } }`, so you can inspect it directly any time.
  - On exit, a `Trigger Log Report` prints per reaction: each distinct (collapsed) color as a truecolor swatch + hue name + RGB/hex, sorted by trigger count. Because the tally is cumulative, this report is meaningful regardless of when you check it. Sustained-but-benign tints (poison/curse) fire far more often than real emergencies, so their large counts stand out as obvious `ignore_colors` candidates. Copy the high-count RGBs into the matching reaction's `ignore_colors`.

- Capture debug mode (optional, isolated): `pxl_capture.py` + `PxlReactionRegistry`
  - Purpose: when a logged color is ambiguous from a single pixel, save a PNG of the surrounding screen region captured **just before** the key is sent, so you can verify by eye whether a trigger was a real event or a misfire.
  - Requires `pip install mss`.
  - Config: `capture_enabled` (default `False`), `capture_dir` (default `captures`), `capture_w` / `capture_h` (region size centered on each reaction's pixel).
  - Files are named `REACTION_YYYYMMDD_HHMMSS_mmm_r-g-b.png`, so each image lines up with its trigger-log color (e.g. a `CV1 ... purple (186,139,207)` misfire). The triggering color is the trailing `r-g-b` token.
  - Sort by color: run `python pxl_capture.py [captures_dir]` (or call `pxl_capture.report_captures()`) to move loose capture PNGs into per-color subfolders named `<hue>_<r>-<g>-<b>`, nested under each reaction (e.g. `captures/CV1/purple_186-139-207/`). Near-identical shades share a folder; the folder with the most images is the obvious ignore-worthy color. Already-sorted images are left in place, so it is safe to re-run as captures accumulate.
  - Isolation: capture is a debugging mechanic and is fully unpluggable. When `capture_enabled` is `False`, reactions use the plain, capture-free `PxlReaction` (no per-trigger flag checks anywhere). To remove it permanently, delete `pxl_capture.py` and the capture block in `PxlReactionRegistry.__init__` plus the `capture_*` attributes; nothing else changes.
  - How it stays branch-free: reactions are built through a factory (`build_reaction`) stored on the registry. Capture mode swaps that factory once at startup for one that builds a `CapturingPxlReaction` subclass whose `trigger()` grabs the region then calls the normal trigger. The grab is in-memory (~1-3 ms on the poll thread); PNG encoding/writing is offloaded to a worker thread.

- Remap color gates: `pxl_remap_maps.py` (`ACTIONS[...]["color_check"]`)
  - `color_check` is a list of conditions that must ALL pass for an action to fire (logical AND). Each condition is `{ "px": int, "py": int, "color": (r, g, b), "match": bool }`.
  - `match` defaults to `True` ("pixel must be this color"); set `match: False` for "pixel must NOT be this color". An omitted/empty `color_check` means no gate. A single condition may be written as a bare dict.
  - Example: replenish a shield only when the ability is ready and the shield is no longer full:

```python
"color_check": [
    { "px": 2194, "py": 1392, "color": (79, 227, 243) },                 # ability ready
    { "px": 1500, "py": 800,  "color": (60, 120, 200), "match": False }, # shield NOT full
]
```

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
  pxl_wincheck.py       # session gating (window title + marker pixel)
  pxl_lib.py            # pixel/color utilities
  pxl_intercept.py      # interception-based keyboard events
  ansi.py               # simple ANSI color helpers for console output
  pyinterception/       # local clone of third-party library (do not modify)
```
