"""Safe display of visitor-written text in a terminal."""

import unicodedata


def printable(text: str) -> str:
    """Drop control characters (ESC, BEL, C1 ...) but keep newlines/tabs and format characters
    such as ZWNJ, which Persian spelling needs."""
    return "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch) != "Cc")
