from __future__ import annotations

import re

_NON_ALNUM_HYPHEN = re.compile(r"[^a-z0-9\-]+")
_WS = re.compile(r"\s+")


def normalize_key(surface: str) -> str:
    s = surface.lower()
    s = _NON_ALNUM_HYPHEN.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    s = s.replace("-", "").replace(" ", "")
    return s


def pick_display_label(variants: dict[str, int]) -> str:
    if not variants:
        return ""
    # Sort by (count desc, length desc, lexicographic asc)
    return sorted(
        variants.items(),
        key=lambda kv: (-kv[1], -len(kv[0]), kv[0]),
    )[0][0]
