# Enhance Remap Sequences
`pxl_remap.py` has been implemented recently; plan the following changes & enhancements.

❔ tags represent areas of particular uncertainty for user; address thoroughly in plan.

## Refactor Mapping Dicts
`pxl_remap_maps.py` has been added to hold configuration data for `pxl_remap.py`.

`REMAPS_OLD` shows the current state, to be replaced by this work. Future state `ACTIONS`, `ROTATIONS` and `REMAPS` take over to separate the dict into components for cleaner reuse.

## Rename "timeout"->"cooldown"
This terminology aligns better with in-game meaning and user's own vocabulary.

## Support "cast_time"
In addition to `cooldown`, `ACTIONS` now have a `cast_time` property representing how much time must pass between the key press and the success of the action itself.

Some actions can be interrupted if another key is pressed before casting is complete, the purpose of `cast_time` is to prevent this within `pxlreact` by ensuring each action's `cast_time` passes uninterrupted before another key event is forwarded to the application.

❔ Ideal system supports *queueing* key presses received prior to the previous actions' completion; queued keys would be popped in order they arrived. *However*, if key queue risks overcomplicating interception loop, suggest a simpler design; a capped queue is also acceptable if this simplifies.

## Combine Map "types"
Current state defines two types of maps: `pixel` and `timed`; these function nearly identically, and in some cases it will be beneficial to have both function in tandem. Combine these models, treating an action with no `color_check` the same as a current `timed` action, and actions without `cast_time` and `cooldown` as we treat current `pixels` -- but also ensure an action that defines both is supported.

❔ If there is a meaningful difference between a None/null `color_check` property and an empty dict, implement the one that is more performant.
