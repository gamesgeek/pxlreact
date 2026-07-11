# pxlreact2 Transition Tracker

This is the **living status document** for the pxlreact2 transition. Every agent session working on
this project must read this file first to understand the overall objective and the current focus.
The vision and requirements behind the transition are in [PXLREACT_2.md](PXLREACT_2.md).

## Overall Objective
Transition `pxlreact` to `pxlreact2` **in-place in this repository**: externalize all inline
configuration, add a lightweight GUI, optimize hot paths, and refresh rules/documentation — without
changing the two core functions (pixel reactions and remap sequences).

## Ground Rules
- Do not modify `pyinterception/` or the underlying intercept driver; be careful in adjacent layers
  (`pxl_intercept.py`), though logical improvements there are welcome.
- No effort spent on backward compatibility with pxlreact1 designs.
- Ignore legacy GUI artifacts and notes (tkinter experiments); GUI library choice is made fresh in Phase 2.
- Each phase ends with a **user-validation gate**: the user verifies behavior against the live game
  before the phase is marked complete and focus advances.
- Each phase gets its own detailed plan when it begins; do not implement ahead of the current focus.

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 0 — Scaffolding & baseline | Tracking doc, transition rule, `requirements.txt`, baseline tag `pxlreact1-final` | Complete |
| 1 — External configuration | External config files (`settings.toml` + `profile.json`) replacing inline config in `PxlReactionRegistry` (`pxlreactHL.py`), `pxl_remap_maps.py`, `pxl_wincheck.py` hard-coded values, and `pxl_keys.py`; retire global `COLOR_TOLERANCE` in favor of per-check tolerance; replace `'reaction': self.react_XX` callables with declarative key-press fields | Complete |
| 2 — Lightweight GUI | GUI for reactions, remaps, and wincheck config, built against the Phase 1 schema; leading candidate is a separate-process GUI editing the config file with a reload signal to the core, keeping the 25 ms polling loop isolated; library selection (DearPyGui / PySide6 / minimal web UI) decided via spikes inside this phase | Not started |
| 3 — Performance review | Profile hot paths (`get_pixel_color`, `PxlReaction.evaluate`, `ColorCondition.passes`) after the refactor stabilizes; optimize high-frequency methods | Not started |
| 4 — Rules & documentation | Retire/update stale Cursor rules (`pxl-react-lite.mdc` must be updated no later than Phase 2) and rewrite `README.md` | Not started |

## Current Focus
**Phase 2 — Lightweight GUI.** Not yet started; begins with a detailed plan. Configuration now
lives in `settings.toml` (manual, low-churn) and `profile.json` (the file the GUI will manage:
reactions, actions, rotations, remaps, wincheck), loaded and validated by `pxl_config.py`. Open
decisions for the Phase 2 plan: GUI library (DearPyGui / PySide6 / minimal web UI, decided via
spikes), the separate-process architecture, and the config-reload signal to the core.

## Hand-Tuned Behaviors (user-supplied)
Behaviors not captured in code comments that a refactor must preserve (timing feel, debounce quirks,
tolerance values tuned by trial and error). *To be filled in by the user before Phase 1 begins.*

- Hand-tuned tolerance values were arrived at by trial and error, but this should be retired in `pxlreact2` in favor of more dynamic settings associated with each color-driven trigger; a global default value can be set, but each individual reaction or ability-readiness check should be tunable, including those associated with the "wincheck" status monitor component

- Input timing, debounce, etc. feels fine; no quirks or nuances

## Decision Log
- **In-place evolution** in this repo (no greenfield package or new repo).
- **Config-first ordering**: external configuration (Phase 1) precedes the GUI (Phase 2), since the
  GUI reads/writes the config schema.
- All current reaction handlers only call `PI.press(<key>)`, so declarative key-press config fields
  fully replace the callable association in `PxlReactionRegistry`.
- `keyboard` package is listed in the README but no longer imported by first-party code; it is not a
  dependency of pxlreact2.
- **Two config files, not one** (Phase 1): `settings.toml` for manual low-churn settings (stdlib
  `tomllib`, supports comments) and `profile.json` for GUI-managed gameplay config (stdlib `json`
  round-trip). The GUI writes only `profile.json`.
- **Normalization at load time** (Phase 1): `pxl_config.py` fills every color check's `tolerance`
  (from `color.default_tolerance` unless set per-check; wincheck markers default to 0 = exact) and
  converts colors to tuples, so runtime code never consults a global default.
- **Archive convention**: deprecated files are moved to `pxlreact1_archive/` rather than deleted;
  `pxl_keys.py` and `pxl_remap_maps.py` moved there in Phase 1.

## Gate History
- **2026-07-11 — Phase 0 gate passed.** Scaffolding committed and tagged (`pxlreact1-final`); user
  validated the baseline against the live game: reactions and remaps fire, input timing and debounce
  feel fine, no quirks to preserve beyond the tolerance notes above.
- **2026-07-11 — Phase 1 gate passed.** All inline configuration migrated to `settings.toml` +
  `profile.json` (loader/validator in `pxl_config.py`); global `COLOR_TOLERANCE` retired for
  per-check tolerances; reaction callables replaced by declarative `press`/`glyph` fields; wincheck
  supports multiple markers; `pxl_keys.py` and `pxl_remap_maps.py` archived. User validated against
  the live game: fully functional. This state is the fallback "pxlreact 1.5" if the GUI work does
  not pan out.
