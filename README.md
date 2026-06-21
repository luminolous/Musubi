---
title: Musubi
emoji: 🧬
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Musubi 🧬

> *Tying entities into hypotheses.*

## About

Musubi extracts four biomedical entity types — **Chemical, Disease, Virus, Gene** — from PubMed abstracts and visualizes their sentence-level co-mentions as an interactive graph. It is designed as a hypothesis filter for **virus-centric drug repurposing**, where pairs like *Virus–Chemical*, *Virus–Gene*, or *Chemical–Disease* hint at candidate drugs, molecular targets, or therapeutic indications.

Co-mention is *not* causal evidence — two entities sharing a sentence does not prove a biological relationship. But the literature is large, and co-mention is a cheap filter for "which pairs are worth a human reading." Musubi surfaces those pairs and the exact sentences they appear in, so every edge in the graph is one click away from the original wording.

Powered by [`lumicero/Joint-Uniform-BioNER`](https://huggingface.co/lumicero/Joint-Uniform-BioNER), a PubMedBERT-based joint NER model trained on a uniformized merge of BC5CDR, NCBI Disease, BC2GM, and a virus subset.

## How to use

1. **Paste abstracts** into the textarea (separate multiple abstracts with a blank line), or click **PubMed search** to fetch them by query.
2. **Click Analyze.** The graph appears in the canvas: nodes are entities (colored by type — Chemical/Disease/Virus/Gene), edges are co-mentions (thicker = more contexts).
3. **Explore.** Click a node to highlight its neighbors. Click an edge to open the evidence panel with the original sentences and entity highlights. Use the confidence slider, pair-type filter, and granularity toggle to refine the view.

**Try these PubMed queries:**

- `SARS-CoV-2 ACE2 spike`
- `hepatitis C ribavirin sofosbuvir`
- `HIV reverse transcriptase zidovudine`

## Configuration

### `ENTREZ_EMAIL` (required for PubMed search)

The `POST /pubmed-search` endpoint uses NCBI Entrez, which requires an email address on every request (NCBI uses it to contact you if your usage pattern overloads their servers, and to enforce per-user rate limits).

- **Local dev**: `export ENTREZ_EMAIL=you@example.com` before launching uvicorn.
- **Hugging Face Space**: add `ENTREZ_EMAIL` as a Space secret under *Settings → Variables and secrets*.

If unset, `/pubmed-search` returns `503` with a clear message — the rest of the app keeps working, you just have to paste abstracts manually.

## Limitations

- **Co-mention ≠ causation.** Two entities in the same sentence may or may not be biologically related. Treat the graph as a hypothesis filter, not as evidence.
- **CPU throughput.** Inference runs on a free-tier CPU (2 vCPU). Expect ~0.3 s per sentence; very large batches will feel slow. Hard cap: 50 abstracts or 500 sentences per request.
- **Naive entity normalization.** Surface forms are grouped by a simple lowercase + alphanumeric key (`SARS-CoV-2` → `sarscov2`, `ACE-2` → `ace2`). There is no linking to external ontologies (MeSH, NCBI Taxonomy, HGNC), so genuinely distinct entities that collapse to the same key would merge.
- **Model coverage.** The underlying model is conservative on some entity surfaces (e.g. may tag only part of a complex token like `SARS-CoV-2`) and may miss low-frequency synonyms. Lowering the confidence slider widens recall at the cost of precision.

## Citation

> _Citation placeholder. A paper is in preparation; once published it will be linked here._

## Acknowledgments

- Model: [`lumicero/Joint-Uniform-BioNER`](https://huggingface.co/lumicero/Joint-Uniform-BioNER)
- Training datasets: BC5CDR, NCBI Disease, BC2GM, and a curated virus subset from PubMed
- Literature source: PubMed via NCBI Entrez
- Sentence splitter: [pysbd](https://github.com/nipunsadvilkar/pySBD)
- Graph rendering: [vis-network](https://visjs.org/)
