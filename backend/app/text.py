"""Safe display of visitor-written text in a terminal."""

import unicodedata

# Bidi embedding/override/isolate controls can reorder what an operator sees (Trojan Source).
# ZWNJ/ZWJ (U+200C/U+200D) are kept: Persian spelling depends on them.
_BIDI_CONTROLS = frozenset("‪‫‬‭‮⁦⁧⁨⁩‎‏؜")


def printable(text: str) -> str:
    """Drop control characters (ESC, BEL, C1 ...) and bidi overrides; keep newlines and tabs."""
    return "".join(
        ch
        for ch in text
        if ch in "\n\t" or (unicodedata.category(ch) != "Cc" and ch not in _BIDI_CONTROLS)
    )


def one_line(text: str) -> str:
    """For single-line fields: a newline can't start a new (forged) line."""
    return " ⏎ ".join(printable(text).splitlines())


def indented(text: str, indent: str) -> str:
    """Multi-line field: every line boundary (incl. U+2028/U+2029) continues under ``indent``."""
    return f"\n{indent}".join(printable(text).splitlines())
