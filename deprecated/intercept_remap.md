# Intercept & Remap
Using `pxl_intercept.py` and its underlying `pyinterception` library, plan the implementation of support for remapping keys to a cycled sequence of other keys, driven by rules of prioritization and preconditions.

Color tests will require `pxl_lib.py` and key handling may involve `pxl_keys.py` but not sure what the best approach is here.

There are two types of prioritization rulesets to support: timed sequences with internal cooldowns assigned to each ability, and pixel-color based prioritization where keys are pressed based on a check of pixel color.

## Intercept Source Key
The desired behavior is that when the user presses the remapped key, `pxlreact` intercepts this key and sends a *different* key instead from among a set of predefined possible keys. Which key it sends depends on preconfigured rules according to the type of remap.

## Timed Sequence
This type of remapping replaces a single key with a sequence of other keys which cycle according to an ordered priority and preset cooldown times. The rule of a timed sequence can be stated as:

- Press the *first* key in the sequence whose cooldown period has passed; if no qualifying key exists, do nothing (no key reaches app)

### Example Timed Sequence

```py
skill_rotation = {
  "fireball": {"key": "r", "timeout": 3.25},
  "volcano": {"key": "f", "timeout": 6.33},
  "ember": {"key": "e", "timeout": 2.2},
  "time_last_pressed": -1
}
```

### Timed Sequence Usage
Using the above example, user would bind for example hardware e key to the skill_rotation sequence, so each actual physical press of e would invoke this queue, sending r, f, e or nothing at all depending on whether any of those skills are "available" meaning they were pressed last longer ago than their timeout indicates.

### Timed Sequence Notes
- No indexing is used here - the sequence is ordered by priority and the timers control the ordering (i.e., when skill 1 is on cooldown, the key will move on and pick skill 2 or 3 and so on).

## Pixel-Color Sequence
For this type of sequence, `pxlreact` sends the first key in a sequence whose color check "passes." This rule can be stated as:

- Press the *first* key in the sequence whose pixel color test returns true.

### Example Pixel-Color Sequence

```py
skill_rotation = {
  "fireball": {"key": "r", "px": 1200, "py": 1100, "color": (125, 32, 99)},
  "volcano": {"key": "f", "px": 950, "py": 888, "color": (155, 132, 79)},
  "ember": {"key": "e", "px": 780, "py": 888, "color": (111, 211, 44),
}
```
### Timed Sequence Usage
Using the above dict, the user might bind this sequence to "e" and when pressed expects `pxlreact` would check each entry in sequence, sending the first key for him the defined pixel location matches the color being tested.

**NOTE**: There may be a more effective way to do this with lambda functions or something, please don't follow this model directly if a superior alternative exists for attaching color tests from `pxl_lib.py` to these checks.

For now, assume the tests are for color similarity (`colors_similar( c1, c2 )`); we can consider adding color difference tests later.

## Terminal Output/Testing
Validating key intercept implementation is notoriously difficult; add carefully crafted terminal output highlighted with `ansi.py` to ensure I can understand what's happening and especially diagnose any problems.

## Initial Tests
Create sample versions of each type of bind and suggest an approach for testing them.

# pyinterception reference
https://pypi.org/project/interception-python/
