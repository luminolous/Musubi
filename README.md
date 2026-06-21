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

Musubi extracts four biomedical entity types (Chemical, Disease, Virus, Gene) from PubMed abstracts and visualizes their co-mentions as an interactive graph. Designed as a hypothesis generator for virus-centric drug repurposing.

Powered by [`lumicero/Joint-Uniform-BioNER`](https://huggingface.co/lumicero/Joint-Uniform-BioNER).

## How to use

1. **Paste abstracts** into the textarea (separate multiple abstracts with a blank line), or click **PubMed search** to fetch them by query.
2. **Click Analyze.** The graph appears in the canvas: nodes are entities (colored by type — Chemical/Disease/Virus/Gene), edges are sentence-level co-mentions (thicker = more contexts).
3. **Explore.** Click a node to highlight its neighbors. Click an edge to open the evidence panel with the original sentences and entity highlights. Use the confidence slider, pair-type filter, and granularity toggle to refine the view.

> _Screenshot placeholder._

## Configuration

### `ENTREZ_EMAIL` (required for PubMed search)

The optional `POST /pubmed-search` endpoint uses NCBI Entrez, which requires
an email address to be set on every request (NCBI uses it to contact you if
your usage pattern overloads their servers, and to enforce per-user rate
limits). Without it, NCBI may block requests entirely.

- **Local dev**: `export ENTREZ_EMAIL=you@example.com` before launching uvicorn.
- **Hugging Face Space**: add `ENTREZ_EMAIL` as a Space secret under
  *Settings → Variables and secrets*.

If the variable is unset, `/pubmed-search` returns `503` with a clear message
and the rest of the app keeps working — you can still paste abstracts manually
into the textarea.
