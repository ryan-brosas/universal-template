<!-- capsule-v2 -->
# stale-chunk-prune-safety-net — what happens to chunks whose parent doc vanished?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** Why does retrieval re-verify doc existence post-search, and what exactly is filtered?

## Post-search deleted-doc pruning
**Path/Symbol:** `Dealer._prune_deleted_chunks` `rag/nlp/search.py:87-129` + helper `_existing_doc_ids` `:74-85`; called from `Dealer.retrieval` `:635`.
**Signature:** `_prune_deleted_chunks(sres: SearchResult) -> SearchResult`.
**Data Shape:** fast path when `len(existing_doc_ids) == len(set(chunk_doc_ids))` returns input untouched (zero extra queries beyond one batched `DocumentService.get_by_ids`).

### Decisive source
```python
# Temporary safety net:
# Some delete paths can leave stale chunks in the doc store if the DB row
# is removed but the vector record is not fully cleaned up. We filter those
# chunks here so chat/retrieval does not surface content from deleted docs.
# Keep this as a fallback, not as the primary delete mechanism.
```

**Flow:** collect `doc_id` from every returned chunk field → one deduped batch existence check against the metadata DB (via thread_pool_exec) → if any missing, rebuild SearchResult keeping only chunks whose doc survived; highlights filtered in lockstep; missing highlight entries tolerated (`filtered_highlight = {} if sres.highlight else sres.highlight` keeps None as None); removal logged with count. `total` becomes len(filtered ids).
**Invariant:** prune runs BEFORE rerank/threshold/pagination in retrieval() so downstream windows never see ghost rows; but it is explicitly documented as a FALLBACK — porters must not treat it as license to skip store-side cascade deletes.
**Probe:** `sed -n '88,92p' rag/nlp/search.py | grep -c 'Temporary safety net'` → 1; `grep -n '_prune_deleted_chunks(sres)' rag/nlp/search.py` → 1 hit :635 (call site); `sed -n '103p' rag/nlp/search.py | grep -c 'filtered_highlight = {} if sres.highlight'` → 1. Executed GREEN at pin.

## Get live surrounding code
**Referenced symbol live-resolved during authoring:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "_prune_deleted_chunks stale chunks deleted docs", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt the batch-check + rebuild-with-filtered-highlights shape; adapt the existence source (any authoritative metadata store); omit nothing — but keep the in-source comment warning that this is a net, not the delete mechanism.
