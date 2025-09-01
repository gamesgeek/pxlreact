"""
poeregex.py is a low-tech tool for Path of Exile players to generate concise regex patterns for
searching in-game stash tabs for high-value items.

No upper-limits are collected or enforced for modifiers, so searches will be for values "greater
than or equal to" the specified low; this helps greater_or_equal_pattern() generate patterns within
the 50-character limit (and in most contexts higher values are still desirable).
"""

RED = "\033[91m"
GRE = "\033[92m"
YEL = "\033[93m"
CYA = "\033[96m"
MAG = "\033[95m"
RES = "\033[0m"

import subprocess


def escape_special_chars( text ):
    """
    Escape common regex metacharacters with single backslashes.
    """
    set_string = r".^$*+?()[]{}|"
    specials = set( set_string )
    escaped = []
    for c in text:
        if c in specials:
            escaped.append( '\\' + c )
        else:
            escaped.append( c )
    return ''.join( escaped )


"""
TASK:
Improve replace_word_wildcard() so it does not require whitespace on both sides of word -- it should
still avoid matching word as substrings e.g., "sword", but it should match word at the start or end of
the string, or with punctuation on either side.
"""


def replace_word_wildcard( text ):
    """
    Enable basic "word wildcarding" in templates by replacing the literal string 'word' with a
    regex pattern matching a word of any length.
    """
    if ' word ' in text:
        text = text.replace( ' word ', ' \\w+ ' )
    return text


def finalize_pattern( pattern ):
    """
    Lowercase the pattern and bound with double quotes.
    In-game search is case-insensitive and requires full-string patterns be bounded by quotes.
    """
    return f'"{pattern.lower()}"'


def trim_pattern( pattern, max_len = 48 ):
    """
    Trim patterns exceeding max_len by removing only leading/trailing
    alphabetic or whitespace characters. Attempts even trimming; if one
    side lacks enough removable chars, biases to the other. If insufficient
    safe chars, errors and returns None.
    """
    if len( pattern ) <= max_len:
        return pattern
    diff = len( pattern ) - max_len

    # count how many safe chars at front
    front_rem = 0
    for c in pattern:
        if c.isalpha() or c.isspace():
            front_rem += 1
        else:
            break

    # count safe chars at back
    back_rem = 0
    for c in reversed( pattern ):
        if c.isalpha() or c.isspace():
            back_rem += 1
        else:
            break

    if front_rem + back_rem < diff:
        print( f"{RED}Error: cannot trim pattern safely to {max_len} characters{RES}" )
        return None

    # allocate removals, favor even split, bias if needed
    rem_front = min( front_rem, diff // 2 )
    rem_back = diff - rem_front
    if rem_back > back_rem:
        rem_back = back_rem
        rem_front = diff - rem_back

    trimmed = pattern[ rem_front:len( pattern ) - rem_back ]
    return trimmed if len( trimmed ) == max_len else None


"""
TASK:
greater_or_equal_pattern() needs a major overhaul; it is making invalid assumptions about the number
of digits in the target values; just because the low value is 8 doesn't mean we're only looking for
single-digit numbers. This method must accommodate all numbers greater than or equal to the low value.
As such, the first improvement will be to rename the method to greater_or_equal_pattern().

Another way to state the purpose of this method is to generate a regex that matches the parameter value
and any larger value, but no smaller values.

An example of where the method currently fails is with the value 8; it generates:
[8-9]
but it should generate:
[8-9]\d*

Likewise, 11 produces (1[1-9]|[2-9]\d), which matches all numbers from 11 to 99, but nothing larger.
"""


# def greater_or_equal_pattern( low ):
def greater_or_equal_pattern( value ):
    """
    Generate a regex pattern using as few characters as possible to match all numbers greater than or
    equal to the parameter value.
    
    The pattern can use capture groups and need not mark them as non-capturing; thes use case does not
    actually make use of the captured values so groups are just for | alternation or similar operations.
    """
    s = str( value )
    d = len( s )

    # Basic range for single-digit numbers (e.g., low=5 -> [5-9])
    if d == 1:
        return f"[{s}-9]"

    # For powers of ten (e.g., low=20 -> [2-9]\d) match same digit-length numbers
    if value % ( 10 ** ( d - 1 ) ) == 0:
        return f"[{s[0]}-9]" + "\\d" * ( d - 1 )

    parts = []
    # Exact-prefix match: same leading digits, last digit >= threshold's last digit
    # e.g., low=39 -> "39" instead of "3[9-9]"
    last = s[ -1 ]
    if last == '9':
        parts.append( s )
    else:
        parts.append( f"{s[:-1]}[{last}-9]" )

    # Higher-digit patterns: earlier digit greater than threshold at that position
    # e.g., low=135 yields:
    #   "1[4-9]\d" matches 140–199
    #   "[2-9]\d\d" matches 200–999
    for pos in range( d - 1 ):
        digit = int( s[ pos ] )
        if digit < 9:
            prefix = s[ :pos ] if pos else ""
            suffix = "\\d" * ( d - pos - 1 )
            parts.append( prefix + f"[{digit+1}-9]" + suffix )

    # Combine alternatives into one capturing group
    return f"({ '|'.join( parts ) })"


def collect_wildcard_values( count ):
    """
    Prompt the user for low values for each '#' wildcard and return a list of lows.
    """
    lows = []
    for i in range( 1, count + 1 ):
        low = int( input( f"{MAG}Low for value {YEL}{i}{RES}: " ) )
        lows.append( low )
    return lows


def replace_wildcards( template ):
    """
    Replace each '#' in the template with its corresponding minimum-value regex.
    Avoid nesting parentheses if the pattern is already grouped.
    """
    text = template
    lows = collect_wildcard_values( text.count( '#' ) )
    for low in lows:
        part = greater_or_equal_pattern( low )
        repl = part if part.startswith( '(' ) and part.endswith( ')' ) else f"({part})"
        text = text.replace( '#', repl, 1 )
    return text


if __name__ == '__main__':
    print( f"{MAG}PoE Regex Maker v0.1{RES}\n" )
    print( f"\tUse templates with text from the modifiers you want, replacing numbers with #." )
    print( f"\tYou can also use 'word' to match any word (e.g., for mulitple elemental resists) e.g.:" )
    print( f"\t{CYA}+#% to word resistance{RES}\n" )
    tmpl = escape_special_chars( input( f"{MAG}Template{RES}: " ).lower() )
    tmpl = replace_word_wildcard( tmpl )
    pattern = replace_wildcards( tmpl )
    if len( pattern ) > 48:
        pattern = trim_pattern( pattern, 48 ) or exit( 1 )
    final = finalize_pattern( pattern )
    print( f"\nRegex: {GRE}{final}{RES}" )
    try:
        subprocess.run( 'clip', input = final, text = True, check = True )
        print( f"({MAG}Copied to Clipboard; CTRL-V to Paste{RES})" )
    except:
        print( f"({RED}Couldn't Copy to Clipboard{RES})" )
