"""Text normalization for matching names across Persian/Arabic spellings and casing."""

import re
import unicodedata

_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ة": "ه", "ۀ": "ه"})
_STRIP = re.compile(r"[‌‍ـً-ٟ]")  # ZWNJ, ZWJ, tatweel, diacritics


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_ARABIC_TO_PERSIAN)
    text = _STRIP.sub("", text)
    return re.sub(r"\s+", " ", text).strip().lower()
