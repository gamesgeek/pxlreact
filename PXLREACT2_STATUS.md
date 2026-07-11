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
| 0 — Scaffolding & baseline | Tracking doc, transition rule, `requirements.txt`, baseline tag `pxlreact1-final` | In progress |
| 1 — External configuration | Single config file replacing inline config in `PxlReactionRegistry` (`pxlreactHL.py`), `pxl_remap_maps.py`, `pxl_wincheck.py` hard-coded values, and `pxl_keys.py`; retire global `COLOR_TOLERANCE` in favor of per-check tolerance; replace `'reaction': self.react_XX` callables with declarative key-press fields | Not started |
| 2 — Lightweight GUI | GUI for reactions, remaps, and wincheck config, built against the Phase 1 schema; leading candidate is a separate-process GUI editing the config file with a reload signal to the core, keeping the 25 ms polling loop isolated; library selection (DearPyGui / PySide6 / minimal web UI) decided via spikes inside this phase | Not started |
| 3 — Performance review | Profile hot paths (`get_pixel_color`, `PxlReaction.evaluate`, `ColorCondition.passes`) after the refactor stabilizes; optimize high-frequency methods | Not started |
| 4 — Rules & documentation | Retire/update stale Cursor rules (`pxl-react-lite.mdc` must be updated no later than Phase 2) and rewrite `README.md` | Not started |

## Current Focus
**Phase 0 — Scaffolding & baseline.**

Remaining before the Phase 0 gate:
- User verifies the baseline runs today (launch `pxlreactHL.py` against the game; confirm reactions
  and remaps fire).
- User records any hand-tuned behaviors below.

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

## Gate History
- (no phases completed yet)
