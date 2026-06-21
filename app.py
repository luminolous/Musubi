"""
Musubi backend.

Manual test (Phase 1):

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

from src.ner import DEVICE, get_predictor
from src.pipeline import split_sentences
from src.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    EvidenceItem,
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


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    t0 = time.perf_counter()

    abstracts = [a for a in req.text.split(req.abstract_separator) if a.strip()]
    if len(abstracts) > MAX_ABSTRACTS:
        raise HTTPException(413, f"Too many abstracts (>{MAX_ABSTRACTS}).")

    sentences = split_sentences(req.text)
    if len(sentences) > MAX_SENTENCES:
        raise HTTPException(413, f"Too many sentences (>{MAX_SENTENCES}).")

    predictor = get_predictor()
    spans_per_sentence = predictor.predict(sentences)

    evidence: dict[str, list[EvidenceItem]] = {}
    raw_key = "_raw"
    raw_items: list[EvidenceItem] = []
    total_entities = 0
    type_counter: Counter[str] = Counter()
    for idx, (sentence, spans) in enumerate(zip(sentences, spans_per_sentence)):
        kept = [s for s in spans if s.confidence >= req.min_confidence]
        total_entities += len(kept)
        for s in kept:
            type_counter[s.type] += 1
        if kept:
            raw_items.append(
                EvidenceItem(context_id=idx, text=sentence, spans=kept)
            )
    if raw_items:
        evidence[raw_key] = raw_items

    stats = Stats(
        total_abstracts=len(abstracts),
        total_sentences=len(sentences),
        total_entities=total_entities,
        entities_per_type={
            "Chemical": type_counter.get("Chemical", 0),
            "Disease": type_counter.get("Disease", 0),
            "Virus": type_counter.get("Virus", 0),
            "Gene": type_counter.get("Gene", 0),
        },
        elapsed_seconds=round(time.perf_counter() - t0, 3),
    )

    return AnalyzeResponse(nodes=[], edges=[], evidence=evidence, stats=stats)
