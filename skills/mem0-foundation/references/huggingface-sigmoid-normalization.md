<!-- capsule-v2 -->
# Reranker score sigmoid normalization — why did min-max scaling get replaced, and what must any replacement preserve?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how are raw cross-encoder logits mapped into the [0,1] rerank_score contract without set-relative collapse?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/huggingface_reranker.py`: `HuggingFaceReranker._normalize_scores` (staticmethod, :64-81); applied at :141-142 when `config.normalize`.
**Signature:** `_normalize_scores(scores: List[float]) -> List[float]` — per-document sigmoid `1/(1+e^-x)`.
**Data Shape:** input = unbounded cross-encoder logits (BAAI/bge-reranker-* family); output = same-length list in (0,1), monotone order-preserving.

### Decisive source
```python
# This replaces the previous min-max scaling, which produced *set-relative*
# scores: the lowest-ranked document was always forced to 0.0, and a single
# document (or any set of tied scores) collapsed to 0.0 — wrongly reporting
# a result as completely irrelevant. Sigmoid scores each document on its own
# merit, so those cases are handled naturally.
if not scores:
    return []
arr = np.asarray(scores, dtype=float)
return (1.0 / (1.0 + np.exp(-arr))).tolist()
```

**Flow:** batches of query-doc pairs scored under torch.no_grad → logits squeezed to floats (ndim-0 single-item case materialized into a list FIRST or .tolist() crashes) → if normalize: sigmoid map → zip+sort DESC → top_k slice → docs COPIED with `rerank_score` added (caller's dicts never mutated); any exception falls back to original-order copies stamped score 0.0 (the double-layered fail-open of the reranker-contract capsule).
**Invariant:** normalization must be ABSOLUTE (per-document), never set-relative — min/max over the candidate set forces the weakest result to 0.0 and collapses singletons/ties, which downstream threshold logic then reads as "completely irrelevant"; sigmoid is monotone so ranking is untouched while scores become comparable across queries. Empty input returns [] without touching numpy.
**Probe:** `grep -n "np.exp(-arr)" mem0/reranker/huggingface_reranker.py` (exactly :81); `grep -n "rerank_score" mem0/reranker/huggingface_reranker.py` (:159 success stamp, :170 fallback stamp).
**Direct test:** `tests/rerankers/test_huggingface_reranker_normalize.py` — 7 cases pin sigmoid arithmetic, [0,1] bounds, argsort preservation, and BOTH regressions by name (`test_single_score_not_collapsed_to_zero` :35, `test_tied_scores_not_collapsed_to_zero` :42). Pure-numpy helper needs no torch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_normalize_scores HuggingFaceReranker sigmoid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt absolute per-document sigmoid normalization for any logit-emitting reranker; adapt the transform only if your model already emits calibrated probabilities (set normalize=False instead of re-normalizing); reverting to min-max reintroduces two documented regression classes. Fully direct-tested (no caveat).
