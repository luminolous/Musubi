from __future__ import annotations

import pysbd

_segmenter = pysbd.Segmenter(language="en", clean=False)


def split_sentences(text: str) -> list[str]:
    return [s for s in _segmenter.segment(text) if s and s.strip()]
