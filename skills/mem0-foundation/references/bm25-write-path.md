<!-- capsule-v2 -->
# BM25 sparse-at-insert — why must keyword indexing happen on the WRITE path, not the read path?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how does a vector store serve hybrid search when its engine needs precomputed sparse vectors?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/qdrant.py`: `insert` BM25 block (:186-246), `_get_bm25_encoder` (:93), `_encode_bm25` (:111), `_has_bm25_slot`; `update` dual-path (:500-536); `keyword_search` (:454).
**Signature:** `insert(vectors, payloads=None, ids=None)` — encodes `payload["text_lemmatized"] or payload["data"]` into a named sparse vector `bm25` alongside the dense `""` vector.
**Data Shape:** named-vector point `{ "": dense, "bm25": SparseVector(indices, values) }`; slot presence detected from collection config (create_col with enable_bm25).

### Decisive source
```python
sparse_results = list(encoder.embed(texts_for_bm25))   # ONE batch call for the page
if len(sparse_results) != len(texts_for_bm25):
    ...raise ValueError("count mismatch")              # → per-row fallback
...
except Exception as e:
    # Fall back to per-row encoding so a single bad input
    # doesn't drop BM25 for the whole batch.
```
```python
# Partial update: use Qdrant's dedicated endpoints.
# Note: BM25 sparse vector cannot be refreshed via set_payload alone;
# payload-only updates will leave any existing BM25 vector stale. In
# practice v3 re-embeds on memory text change, so this is acceptable.
if payload is not None:
    self.client.set_payload(...)      # payload-only lane: STALE bm25
if vector is not None:
    self.client.update_vectors(...)   # vector lane: re-encodes bm25
```

**Flow:** insert batches all lemmatized texts through fastembed once (per-row fallback on any failure) and attaches sparse vectors at upsert; update chooses full-upsert (re-encodes bm25) vs partial endpoints (payload-only leaves stale bm25 — accepted because v3 always re-embeds on text change); `keyword_search` queries the prebuilt sparse index with the lemmatized query.
**Invariant:** BM25 is materialized at WRITE time because the read path can't afford encoding the whole corpus per query; the memory layer cooperates by storing `text_lemmatized` in every payload (main.py :1026-1031); stores WITHOUT a bm25 slot skip silently (`_has_bm25_slot`) so the same code serves plain-dense collections.
**Probe:** `tests/vector_stores/test_qdrant.py::test_insert_batches_bm25_encoding` (:114), `::test_insert_skips_bm25_when_slot_missing` (:161), `::test_insert_falls_back_to_per_row_on_batch_failure` (:177), `::test_update_with_none_vector_uses_set_payload` (:363).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "qdrant insert bm25 sparse vector text_lemmatized fastembed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt write-time sparse materialization + slot detection + batch-with-per-row-fallback; adapt encoder choice; document the stale-bm25-on-payload-only-update tradeoff rather than fixing it.
