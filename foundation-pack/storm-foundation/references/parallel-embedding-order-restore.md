<!-- capsule-v2 -->
# Parallel embedding order-restore — how do you embed N texts concurrently and still return them in input order?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** What is the failure mode of `as_completed` embedding fan-out and the minimal fix?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/encoder.py:Encoder._get_text_embeddings` (:132-178).
**Signature:** `_get_text_embeddings(texts: Union[str, List[str]], max_workers: int = 5) -> np.ndarray`; public `encode(texts, max_workers=5)`; single-string path returns 1-D array.
**Data Shape:** Input str|List[str]; output np.ndarray (2-D for lists, rows aligned to inputs). Token usage accumulated on `self.total_token_usage`, drained via `get_total_token_usage(reset=True)`.

### Decisive source
```python
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    futures = {executor.submit(self._get_single_text_embedding, text): text for text in texts}
    for future in as_completed(futures):
        try:
            text, embedding, tokens = future.result()
            embeddings.append((text, embedding, tokens))   # keep text BESIDE its vector
            total_tokens += tokens
        except Exception as e:
            print(f"An error occurred for text: {futures[future]}")   # drop, don't raise
embeddings.sort(key=lambda x: texts.index(x[0]))           # ORDER RESTORE by first occurrence
self.total_token_usage += total_tokens
return np.array(embeddings)
```

**Flow:** Each text → `litellm.embedding(model=..., caching=True)` in a worker → results collected out-of-order as (text, embedding, tokens) triples → sorted back to input order via `texts.index` → stacked. Failed texts are dropped with a print, shrinking the output.
**Invariant:** (1) Without the sort, callers that zip embeddings against their query/snippet arrays silently MISATTRIBUTE vectors — this is THE bug the capsule prevents. (2) The restore uses `texts.index(first-match)` so DUPLICATE texts all map to the first index (order stable only for distinct inputs). (3) Per-item exceptions degrade to short outputs; downstream cosine similarity then sees fewer columns than urls if used raw — consumers must treat length mismatch as an error. (4) Embedding responses go through litellm's disk cache (`caching=True`), so re-encodes across runs are free.
**Probe:** deterministic pin GREEN — encoder.py:174 `embeddings.sort(key=lambda x: texts.index(x[0]))` byte-verified this pass; error-swallow branch at :169-171.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "Encoder _get_text_embeddings sort input order", limit: 10 });
```

## Verdict
Adopt the carry-text-beside-vector + sort-by-input pattern for any concurrent embedding; replace `texts.index` with enumerate-keyed dict for duplicate-heavy inputs; omit nothing else. Note Co-STORM's KnowledgeBase caches structure embeddings behind a `hash(outline_string)` gate (`kb_embedding["hash"]`) — recompute-only-on-change is the companion contract. Caveat: no upstream tests; source-pinned.
