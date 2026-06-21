from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations

import pysbd

from .normalize import normalize_key, pick_display_label
from .schemas import Edge, EvidenceItem, Node, Span

_segmenter = pysbd.Segmenter(language="en", clean=False)


def split_sentences(text: str) -> list[str]:
    return [s for s in _segmenter.segment(text) if s and s.strip()]


def _edge_id(a: str, b: str) -> str:
    lo, hi = sorted([a, b])
    return f"e_{lo}__{hi}"


def _pair_type(a: str, b: str) -> str:
    lo, hi = sorted([a, b])
    return f"{lo}-{hi}"


def aggregate_comentions(
    contexts: list[tuple[int, str, list[Span]]],
) -> tuple[list[Node], list[Edge], dict[str, list[EvidenceItem]]]:
    """
    contexts: list of (context_id, context_text, spans).
    Returns (nodes, edges, evidence) per SPEC section 5/6.
    """
    # Per-key: type (first seen wins; assume consistent), variant counts, total count
    key_type: dict[str, str] = {}
    key_variants: dict[str, Counter[str]] = defaultdict(Counter)
    key_count: Counter[str] = Counter()

    # Per-edge: weight, evidence list
    edge_weight: Counter[str] = Counter()
    edge_meta: dict[str, tuple[str, str, str]] = {}  # edge_id -> (source, target, pair_type)
    evidence: dict[str, list[EvidenceItem]] = defaultdict(list)

    for ctx_id, ctx_text, spans in contexts:
        # Build unique (key, type) per context for pairing; count surface variants
        ctx_keys: dict[str, str] = {}  # key -> type
        for sp in spans:
            k = normalize_key(sp.text)
            if not k:
                continue
            key_type.setdefault(k, sp.type)
            key_variants[k][sp.text] += 1
            key_count[k] += 1
            ctx_keys[k] = sp.type

        # Iterate unordered pairs of unique keys in this context
        for a, b in combinations(sorted(ctx_keys.keys()), 2):
            eid = _edge_id(a, b)
            edge_weight[eid] += 1
            if eid not in edge_meta:
                lo, hi = sorted([a, b])
                edge_meta[eid] = (
                    lo,
                    hi,
                    _pair_type(ctx_keys[a], ctx_keys[b]),
                )
            evidence[eid].append(
                EvidenceItem(context_id=ctx_id, text=ctx_text, spans=spans)
            )

    # Drop nodes with 0 edges
    active_keys: set[str] = set()
    for eid in edge_weight:
        lo, hi, _ = edge_meta[eid]
        active_keys.add(lo)
        active_keys.add(hi)

    nodes: list[Node] = []
    for k in sorted(active_keys):
        variants = key_variants[k]
        nodes.append(
            Node(
                id=k,
                label=pick_display_label(dict(variants)),
                type=key_type[k],  # type: ignore[arg-type]
                count=key_count[k],
                variants=[v for v, _ in variants.most_common()],
            )
        )

    edges: list[Edge] = []
    for eid, w in edge_weight.items():
        src, tgt, ptype = edge_meta[eid]
        edges.append(
            Edge(id=eid, source=src, target=tgt, weight=w, pair_type=ptype)
        )

    return nodes, edges, dict(evidence)
