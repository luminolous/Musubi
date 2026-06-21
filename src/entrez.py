from __future__ import annotations

import os
import socket
from io import BytesIO

from Bio import Entrez

MAX_RESULTS_CAP = 50
TIMEOUT = 30


def search_pubmed(
    query: str,
    max_results: int = 20,
    email: str | None = None,
) -> list[dict]:
    """Search PubMed and return [{'pmid','title','abstract'}, ...].

    Skips records without an abstract. Caps max_results at 50.
    Raises ValueError if no email is configured (NCBI requires it).
    """
    email = email or os.environ.get("ENTREZ_EMAIL")
    if not email:
        raise ValueError(
            "ENTREZ_EMAIL is required by NCBI Entrez. Set the environment "
            "variable or pass email explicitly."
        )

    Entrez.email = email
    socket.setdefaulttimeout(TIMEOUT)
    max_results = min(max(int(max_results), 1), MAX_RESULTS_CAP)

    handle = Entrez.esearch(
        db="pubmed", term=query, retmax=max_results, sort="relevance"
    )
    try:
        search = Entrez.read(handle)
    finally:
        handle.close()
    pmids = list(search.get("IdList", []))
    if not pmids:
        return []

    handle = Entrez.efetch(
        db="pubmed", id=",".join(pmids), rettype="abstract", retmode="xml"
    )
    try:
        raw = handle.read()
    finally:
        handle.close()
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    records = Entrez.read(BytesIO(raw))

    out: list[dict] = []
    for article in records.get("PubmedArticle", []):
        try:
            medline = article["MedlineCitation"]
            pmid = str(medline.get("PMID", ""))
            art = medline.get("Article", {})
            title = str(art.get("ArticleTitle", "")).strip()
            abstract_node = art.get("Abstract")
            if not abstract_node:
                continue
            parts = abstract_node.get("AbstractText", [])
            if not parts:
                continue
            chunks: list[str] = []
            for p in parts:
                label = getattr(p, "attributes", {}).get("Label") if hasattr(p, "attributes") else None
                text = str(p).strip()
                if not text:
                    continue
                chunks.append(f"{label}: {text}" if label else text)
            abstract = " ".join(chunks).strip()
            if not abstract:
                continue
            out.append({"pmid": pmid, "title": title, "abstract": abstract})
        except (KeyError, TypeError, AttributeError):
            continue
    return out
