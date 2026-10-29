"""Versioned prompt templates. The version (a hash of the template text) goes into every trace so
an answer can be tied to the exact prompt that produced it."""

import hashlib
from functools import lru_cache
from pathlib import Path
from string import Template

_DIR = Path(__file__).parent


@lru_cache
def _template(name: str) -> tuple[Template, str]:
    raw = (_DIR / f"{name}.md").read_text(encoding="utf-8")
    return Template(raw), hashlib.sha256(raw.encode()).hexdigest()[:8]


def load_prompt(name: str, **values: str) -> tuple[str, str]:
    template, version = _template(name)
    return template.substitute(values), version
