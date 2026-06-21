from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EntityType = Literal["Chemical", "Disease", "Virus", "Gene"]
Granularity = Literal["sentence", "abstract"]


class Span(BaseModel):
    start: int
    end: int
    type: EntityType
    text: str
    confidence: float


class Node(BaseModel):
    id: str
    label: str
    type: EntityType
    count: int
    variants: list[str]


class Edge(BaseModel):
    id: str
    source: str
    target: str
    weight: int
    pair_type: str


class EvidenceItem(BaseModel):
    context_id: int
    text: str
    spans: list[Span]


class Stats(BaseModel):
    total_abstracts: int
    total_sentences: int
    total_entities: int
    entities_per_type: dict[str, int]
    elapsed_seconds: float


class AnalyzeRequest(BaseModel):
    text: str
    granularity: Granularity = "sentence"
    min_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    abstract_separator: str = "\n\n"


class AnalyzeResponse(BaseModel):
    nodes: list[Node]
    edges: list[Edge]
    evidence: dict[str, list[EvidenceItem]]
    stats: Stats


class PubMedSearchRequest(BaseModel):
    query: str
    max_results: int = Field(default=20, ge=1, le=50)


class PubMedAbstract(BaseModel):
    pmid: str
    title: str
    abstract: str


class PubMedSearchResponse(BaseModel):
    abstracts: list[PubMedAbstract]
