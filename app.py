"""
Musubi backend.

Manual test:

  curl -X POST http://localhost:7860/analyze \
    -H "Content-Type: application/json" \
    -d '{"text":"The SARS-CoV-2 spike protein binds to ACE2.","granularity":"sentence","min_confidence":0.5}'
"""
from __future__ import annotations

import time
from collections import Counter

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.entrez import search_pubmed
from src.ner import DEVICE, get_predictor
from src.pipeline import aggregate_comentions, split_sentences
from src.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    PubMedAbstract,
    PubMedSearchRequest,
    PubMedSearchResponse,
    Span,
    Stats,
)

MAX_ABSTRACTS = 50
MAX_SENTENCES = 500

app = FastAPI(title="Musubi")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def _startup() -> None:
    get_predictor()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model_loaded": True, "device": DEVICE}


@app.get("/")
def index() -> FileResponse:
    return FileResponse("static/index.html")


def _split_abstracts(text: str, sep: str) -> list[str]:
    return [a.strip() for a in text.split(sep) if a.strip()]


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    t0 = time.perf_counter()

    abstracts = _split_abstracts(req.text, req.abstract_separator)
    if len(abstracts) > MAX_ABSTRACTS:
        raise HTTPException(413, f"Too many abstracts (>{MAX_ABSTRACTS}).")

    predictor = get_predictor()

    # Per-sentence inference always (model batches sentences).
    # Build contexts list depending on granularity.
    contexts: list[tuple[int, str, list[Span]]] = []
    total_sentences = 0
    type_counter: Counter[str] = Counter()
    total_entities = 0

    if req.granularity == "sentence":
        sentences = split_sentences(req.text)
        total_sentences = len(sentences)
        if total_sentences > MAX_SENTENCES:
            raise HTTPException(413, f"Too many sentences (>{MAX_SENTENCES}).")
        spans_per_sent = predictor.predict(sentences)
        for idx, (sent, spans) in enumerate(zip(sentences, spans_per_sent)):
            kept = [s for s in spans if s.confidence >= req.min_confidence]
            total_entities += len(kept)
            for s in kept:
                type_counter[s.type] += 1
            contexts.append((idx, sent, kept))
    else:  # abstract
        for a_idx, abstract in enumerate(abstracts):
            sentences = split_sentences(abstract)
            total_sentences += len(sentences)
            if total_sentences > MAX_SENTENCES:
                raise HTTPException(413, f"Too many sentences (>{MAX_SENTENCES}).")
            spans_per_sent = predictor.predict(sentences) if sentences else []
            collected: list[Span] = []
            for sent, spans in zip(sentences, spans_per_sent):
                # Re-base char offsets onto the full abstract text
                base = abstract.find(sent)
                if base < 0:
                    base = 0
                for s in spans:
                    if s.confidence < req.min_confidence:
                        continue
                    collected.append(
                        Span(
                            start=s.start + base,
                            end=s.end + base,
                            type=s.type,
                            text=s.text,
                            confidence=s.confidence,
                        )
                    )
            total_entities += len(collected)
            for s in collected:
                type_counter[s.type] += 1
            contexts.append((a_idx, abstract, collected))

    nodes, edges, evidence = aggregate_comentions(contexts)

    stats = Stats(
        total_abstracts=len(abstracts),
        total_sentences=total_sentences,
        total_entities=total_entities,
        entities_per_type={
            "Chemical": type_counter.get("Chemical", 0),
            "Disease": type_counter.get("Disease", 0),
            "Virus": type_counter.get("Virus", 0),
            "Gene": type_counter.get("Gene", 0),
        },
        elapsed_seconds=round(time.perf_counter() - t0, 3),
    )

    return AnalyzeResponse(
        nodes=nodes, edges=edges, evidence=evidence, stats=stats
    )


@app.post("/pubmed-search", response_model=PubMedSearchResponse)
def pubmed_search(req: PubMedSearchRequest) -> PubMedSearchResponse:
    try:
        results = search_pubmed(req.query, req.max_results)
    except ValueError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(503, f"PubMed fetch failed: {e}")
    return PubMedSearchResponse(
        abstracts=[PubMedAbstract(**r) for r in results]
    )
