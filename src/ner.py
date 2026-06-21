from __future__ import annotations

import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from .schemas import Span

MODEL_ID = "lumicero/Joint-Uniform-BioNER"
DEVICE = "cpu"
BATCH_SIZE = 8
MAX_LENGTH = 256

_predictor: "NERPredictor | None" = None


class NERPredictor:
    def __init__(self, model_id: str = MODEL_ID):
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForTokenClassification.from_pretrained(model_id)
        self.model.to(DEVICE)
        self.model.eval()
        self.id2label = self.model.config.id2label

    @torch.no_grad()
    def predict(self, sentences: list[str]) -> list[list[Span]]:
        results: list[list[Span]] = []
        for i in range(0, len(sentences), BATCH_SIZE):
            batch = sentences[i : i + BATCH_SIZE]
            results.extend(self._predict_batch(batch))
        return results

    def _predict_batch(self, batch: list[str]) -> list[list[Span]]:
        enc = self.tokenizer(
            batch,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_offsets_mapping=True,
        )
        offsets_batch = enc.pop("offset_mapping").tolist()
        enc = {k: v.to(DEVICE) for k, v in enc.items()}
        logits = self.model(**enc).logits
        probs = torch.softmax(logits, dim=-1)
        max_probs, pred_ids = probs.max(dim=-1)
        max_probs = max_probs.cpu().tolist()
        pred_ids = pred_ids.cpu().tolist()

        out: list[list[Span]] = []
        for sent_idx, sentence in enumerate(batch):
            offsets = offsets_batch[sent_idx]
            labels = [self.id2label[p] for p in pred_ids[sent_idx]]
            confs = max_probs[sent_idx]
            spans = self._decode_bio(sentence, offsets, labels, confs)
            out.append(spans)
        return out

    def _decode_bio(
        self,
        sentence: str,
        offsets: list[list[int]],
        labels: list[str],
        confs: list[float],
    ) -> list[Span]:
        valid = {"Chemical", "Disease", "Virus", "Gene"}
        # Token-level spans: (start, end, type, conf)
        token_spans: list[tuple[int, int, str, float]] = []
        for (s, e), label, conf in zip(offsets, labels, confs):
            if s == 0 and e == 0:
                continue
            if label == "O" or label is None:
                continue
            ent = label.split("-", 1)[1] if "-" in label else label
            if ent not in valid:
                continue
            token_spans.append((s, e, ent, conf))

        # Merge adjacent same-type token spans separated only by non-alnum
        # filler (hyphens, spaces). Most BIO models here emit B-X per subword.
        spans: list[Span] = []
        i = 0
        while i < len(token_spans):
            s, e, ent, c = token_spans[i]
            confs_acc = [c]
            j = i + 1
            while j < len(token_spans):
                ns, ne, nent, nc = token_spans[j]
                if nent != ent:
                    break
                gap = sentence[e:ns]
                if gap and any(ch.isalnum() for ch in gap):
                    break
                e = ne
                confs_acc.append(nc)
                j += 1
            text = sentence[s:e]
            if text.strip():
                spans.append(
                    Span(
                        start=s,
                        end=e,
                        type=ent,  # type: ignore[arg-type]
                        text=text,
                        confidence=float(sum(confs_acc) / len(confs_acc)),
                    )
                )
            i = j
        return spans


def get_predictor() -> NERPredictor:
    global _predictor
    if _predictor is None:
        _predictor = NERPredictor()
    return _predictor
