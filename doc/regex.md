# Project Overview: poeregex
Collaborate with me on a project to build a simple Python module capable of generating regular expressions for use by players of the Path of Exile online multiplayer game.

While the objective of this tool is conceptually simple, it faces two primary challenges:
1. The search interface in game is limited to 50 characters and the regex pattern must be bounded by double quotes; therefore the full pattern must be 48 or fewer characters in length.
2. Matching numbers "greater than or equal to" a given value can challenging for certain values; for example, matching all numbers greater than 11 requires excluding 10 but including 100 and above.

# Regex Constraints
The regular expressions produced by poeregex must adhere to the following constraints and guidelines:

- They must be 50 or fewer characters in length
- To enforce a "full string" match, the regex must be bounded by double-quotes, meaning the pattern itself has a true limit of 48 characters
- Although some sample data will contain capital letters, the in-game search interface is not case sensitive so the patterns can include lowercase only
- No upper-bounds should be imposed unle

# Response Guidance
- Where you see existing completed regex, assume we have worked on those together and validated them; where you see *TODO* tags is where we are currently working to create new regex.
- For each new request, provide your regular expression in additional to a few sample strings for validation; include strings that do and do not match the pattern. Remember to replace (#-#) with one of the possible values within that range in your test data
- In your test data, do not include capital letters
- When providing test data, do not use side-by-side columns, tables, or other formatting; provide test data so it can easily be copy-pasted into regex101.com's validation interface (i.e., just give me raw text)
- Some existing regex begin with a single space character - this denotes that the pattern being matched is an internal substring beginning after a previous word; do not begin all regexes with a space by default unless the patterns to be matched indicate the need for such.
- If you find any trailing whitespace in the sample data, ignore it. This is likely a result of copy-pasting and not an actual part of the pattern to match.

# Example Regex: Physical Damage (1-Handed Weapons)
The following 3 lines represent 3 tiers of possible modifier that a 1-handed weapon can exhibit in the game. Each tier has a distinct range of possible values.

Adds (16-24) to (28-42) Physical Damage
Adds (21-31) to (36-53) Physical Damage
Adds (26-39) to (44-66) Physical Damage

The goal of our regular expression (in addition to adhering to the constraints described above) is to find items whose minimum and maximum values are at least the average of the lowest of these three tiers. In this case, the lowest tier is:

Adds (16-24) to (28-42) Physical Damage

The average of the minimum of this range is (16 + 24)/2 = 20, while the maximum is (28+42)/2 = 35. Our regex should therefore look for modifiers with a low value greater than or equal to 20 and a high value greater than or equal to 35. Here is that regex, recalling the constraints of character limit and quote bounding:

"  [2-9]\d to ([3-9][5-9]|[4-9]\d) physical d"

`NOTE`: when an average value comes out to be a fraction, round the value down before building the regex (e.g., if the average is 75.4, the regex should target 74 or above)

`NOTE`: some items will have modifier categories with fewer than 3 tiers; always target the average of the lowest tier as the "starting point" for the regex matching range (this should work even if we only want to look for one tier)

## 1-Handed Melee (COMPLETED)
The following modifier tiers and ranges can appear on 1-handed weapons:

### Raw Added Damage (1-Handed Melee)

`Modifier Tiers (Physical):`
Adds (16-24) to (28-42) Physical Damage
Adds (21-31) to (36-53) Physical Damage
Adds (26-39) to (44-66) Physical Damage

`Added Physical Damage Regex:`
"  [2-9]\d to ([3-9][5-9]|[4-9]\d) physical d"

`NOTE`: The regex for physical damage here includes a few additional characters to avoid a conflicting match with "Adds # to # Physical Thorns Damage" modifiers which are less desirable

`Modifier Tiers (Fire):`
Adds (35-52) to (53-79) Fire Damage
Adds (45-67) to (68-102) Fire Damage
Adds (52-78) to (79-119) Fire Damage

`Added Fire Damage Regex::`
"  (4[4-9]|[5-9]\d) to (6[6-9]|[7-9]\d) fire"

`Modifier Tiers (Cold):`
Adds (28-43) to (44-65) Cold Damage
Adds (37-55) to (56-84) Cold Damage
Adds (42-63) to (64-95) Cold Damage

`Added Cold Damage Regex::`
"  (3[6-9]|[4-9]\d) to (5[5-9]|[6-9]\d) cold"

`Modifier Tiers (Lightning):`
Adds (1-7) to (86-123) Lightning Damage
Adds (1-8) to (108-155) Lightning Damage
Adds (1-10) to (125-180) Lightning Damage

`Added Lightning Damage Regex:`
"Adds ([4-9]|10) to (10[5-9]|1[1-9]\d) lightning damage"

### % Increased Damage (1-Handed Melee)
For modifier tiers that include only a single range, apply a similar approach. The regex should target values at or above the average of the lowest tier.

`Modifier Tiers (Physical):`
(135-154)% increased Physical Damage
(155-169)% increased Physical Damage
(170-179)% increased Physical Damage

`Physical Damage % Regex:`
"(14[4-9]|1[5-9]\d|[2-9]\d{2})% increased phys"

`Modifier Tiers (Elemental):`
(63-71)% increased Elemental Damage with Attacks
(73-85)% increased Elemental Damage with Attacks
(87-100)% increased Elemental Damage with Attacks

`Elemental Damage % Regex:`
"(6[7-9]|[7-9]\d|1\d\d)% increased elemental d"

### Increased Skill Level (1-Handed Melee)

`Modifier Tiers (Skill Level):`
+3 to Level of all Melee Skills
+4 to Level of all Melee Skills
+5 to Level of all Melee Skills

`Melee Skill Level Regex:`
"\+[2-9].*?all melee"

`NOTE`: Adjusting the range can match this bonus on Gloves as well (+2 maximum)
