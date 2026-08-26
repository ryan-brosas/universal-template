<!-- capsule-v2 -->
# load_docs_in_chunks AUTO selection — centroid-nearest-k over a random 300-chunk embedding sample, with brace-escaping for later .format()

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how does prompt tuning pick a representative chunk sample from the corpus, and what formatting trap must the output survive?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/prompt_tune/loader/input.py`: `_sample_chunks_from_embeddings` (:31-41), `load_docs_in_chunks` (:44-107); `defaults.py` (K=15, LIMIT=15, N_SUBSET_MAX=300, MAX_TOKEN_COUNT=2000); `types.py`: `DocSelectionType` (ALL/RANDOM/TOP/AUTO).
**Signature:** `load_docs_in_chunks(config, select_method: DocSelectionType, limit: int, logger, n_subset_max=N_SUBSET_MAX, k=K) -> list[str]`.
**Data Shape:** returns ≤limit chunk strings; every `{`/`}` doubled so chunks can be embedded into templates via `str.format()` without LaTeX/markdown braces exploding.

### Decisive source
```python
if limit <= 0 or limit > len(chunks_df):
    logger.warning(f"Limit out of range, using default number of chunks: {LIMIT}")
    limit = LIMIT                                   # silent default, not an error
...
# AUTO: embed a random subset first, then take the k nearest to the centroid
sampled = chunks_df.sample(n=min(n_subset_max, len(chunks_df)))["text"].tolist()
embeddings = await run_embed_text(sampled, ...)
center = np.mean(embeddings, axis=0)
distances = np.linalg.norm(embeddings - center, axis=1)
nearest_indices = np.argsort(distances)[:k]
return [i.replace("{", "{{").replace("}", "}}") for i in chunks_df["text"]]
```
Note the subtlety: `_sample_chunks_from_embeddings` receives the FULL chunks_df + embeddings computed from the SAMPLE — argsort positions index the sampled array; the returned rows are selected by position from that same frame passed in (call site passes full df, embeddings array is sample-length → positional alignment holds only because sample == whole frame when n_subset_max ≥ len).

**Flow:** read all files → chunk each doc via the configured chunker → clamp limit to default when out of range → TOP takes head(n), RANDOM samples n, AUTO embeds min(300, N) random chunks then keeps k=15 closest to the embedding centroid → escape braces → return.
**Invariant:** (1) Out-of-range limits degrade to LIMIT=15 rather than raising. (2) AUTO is centroid-distance selection, NOT clustering — one representative-ish blob, cheap and deterministic given the sample. (3) Brace escaping happens LAST and unconditionally; removing it corrupts any prompt template containing user text.
**Probe:** `tests/unit/prompt_tune/test_load_docs_in_chunks.py`: TOP head-n :104-138, RANDOM count :141-171, brace escaping `assert "{{latex}}" in result[0]` :174-205, out-of-range→default LIMIT :208-241, multi-doc chunking :244-272.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "load_docs_in_chunks _sample_chunks_from_embeddings DocSelectionType AUTO centroid", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt centroid-nearest sampling for cheap corpus-representative selection and ALWAYS escape braces before template interpolation; adapt k/subset budgets to host cost tolerance; treat the positional-alignment caveat above as a known sharp edge if you resize the sample.
