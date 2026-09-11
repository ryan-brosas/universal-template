<!-- capsule-v2 -->
# SentenceTransformer cross-encoder scoring — local pair prediction, numpy-to-float normalization

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does a LOCAL (no-API) reranker produce comparable scores and where does its top_k cut happen?

## Connected graph-selected seam
**Path/Symbol:** `mem0/reranker/sentence_transformer_reranker.py`: `SentenceTransformerReranker.rerank` (:52-115); model construction at :51 (`self.model = CrossEncoder(self.config.model, device=self.config.device)`).
**Signature:** `rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]`.
**Data Shape:** query+doc texts → `[[query, doc_text]]` pairs → CrossEncoder raw scores (possibly np.ndarray) → Python floats on the output dicts.

### Decisive source
```python
pairs = [[query, doc_text] for doc_text in doc_texts]
scores = self.model.predict(
    pairs,
    batch_size=self.config.batch_size,
    show_progress_bar=self.config.show_progress_bar,
)
if isinstance(scores, np.ndarray):
    scores = scores.tolist()

doc_score_pairs = list(zip(documents, scores))
doc_score_pairs.sort(key=lambda x: x[1], reverse=True)

final_top_k = top_k or config.top_k
if final_top_k:
    doc_score_pairs = doc_score_pairs[:final_top_k]
...
reranked_doc['rerank_score'] = float(score)
```

**Flow:** build one (query, doc) pair per document → single batched `predict` → ndarray coerced to list → zip docs with scores POSITIONALLY → sort descending → slice with the two-rung ladder (`top_k` arg beats config) → stamp `float(score)` onto copies.
**Invariant:** the positional zip is only safe because scores arrive in input order — a port that lets the predictor shuffle order corrupts every pairing; the explicit `np.ndarray → tolist()` + `float(score)` coercion guarantees JSON-serializable plain floats in results (raw numpy floats leak into payloads otherwise). This is the family's zero-network member: no API key, failure modes are local (model load, OOM) — but it still wraps everything in the same batch 0.0 fail-open as its API siblings.
**Probe:** `grep -cF 'self.model = CrossEncoder(self.config.model, device=self.config.device)' mem0/reranker/sentence_transformer_reranker.py` (=1); `grep -cF 'pairs = [[query, doc_text] for doc_text in doc_texts]' mem0/reranker/sentence_transformer_reranker.py` (=1).
**Coverage caveat (scoped):** CrossEncoder pair scoring itself is untested upstream; `test_reranker_public_exports.py` pins the class export. Keep the caveat when porting the local-model arm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "CrossEncoder predict pairs batch_size rerank", limit: 10 });
```

## Verdict
Adopt pair-batch predict + positional zip + float coercion for any local cross-encoder ranker; adapt model name/batch size via config; omit streaming/incremental scoring that breaks the sort-then-slice contract.
