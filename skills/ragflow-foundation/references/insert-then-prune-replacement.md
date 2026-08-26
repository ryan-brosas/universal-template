<!-- capsule-v2 -->
# Insert-then-prune report replacement — what write order makes a crash mid-refresh leave the OLD complete set instead of a partial one?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** How are community-report rows replaced in the doc store without ever exposing the delete-everything intermediate state?

## Deterministic ids + snapshot-before-insert + exact stale prune
**Path/Symbol:** `rag/graphrag/general/index.py:extract_community` (:937-1015).
**Signature:** chunk id via `chunk_id({"content_with_weight": f"community_report::{title}", "kb_id": kb_id})` — deterministic across reruns.
**Data Shape:** Rows: `knowledge_graph_kwd="community_report"`, `docnm_kwd=title`, tokenized content fields, `weight_flt`, `entities_kwd`/`important_kwd` = member entities, `source_id` = all graph source docs.

### Decisive source
```python
# Deterministic id derived from (kb_id, community title) so reruns of
# extract_community produce stable ids.  Combined with insert-then-
# prune below, this means a crash mid-insert leaves the prior set of
# community reports intact -- never the partial-delete state the old
# delete-then-insert order produced.

old_ids: list[str] = []
try:
    existing_res = await thread_pool_exec(settings.docStoreConn.search,
        ["id"], [], {"knowledge_graph_kwd": ["community_report"]}, [],
        OrderByExpr(), 0, 10000, search.index_name(tenant_id), [kb_id])
    old_ids = list(settings.docStoreConn.get_fields(existing_res, ["id"]).keys())
except Exception:
    # fall back to legacy delete-all-then-insert rather than a mix
    await thread_pool_exec(settings.docStoreConn.delete, {...}, ...)

await insert_chunks_bounded(chunks, tenant_id, kb_id, ...)      # NEW rows first
stale_ids = [i for i in old_ids if i not in new_ids]
if stale_ids:
    try:
        await thread_pool_exec(settings.docStoreConn.delete,
            {"knowledge_graph_kwd": ["community_report"], "id": stale_ids}, ...)
    except Exception:
        logging.exception("Failed to prune %d stale community reports ...")
```

**Flow:** build all new chunks with deterministic ids → snapshot existing ids (bounded at 10k) → insert new rows → delete exactly `{old − new}` → cleanup checkpoints. Failure semantics per stage: snapshot fails ⇒ legacy full-delete fallback; insert fails ⇒ old set intact; prune fails ⇒ stale duplicates linger but current data is correct.
**Invariant:** New rows are durably present before ANY deletion; deletions target only explicit stale ids; deterministic ids make re-inserts idempotent (same id overwrites/updates rather than duplicating).

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "run_graphrag_for_kb merge graph community resolution cancel", filePattern: "*index.py", fields: ["lines","signature"] }); // rank-2 extract_community :897-1019
await mcp.codebase_memory.trace_path({ project: "ragflow", function_name: "save_checkpoint", direction: "inbound" }); // community_reports_extractor + index.py as writers
```
**Probe:** No direct test pins this ordering at the pin — the invariant is documented inline at the decisive range and mirrors the family contract already captured in `stale-chunk-prune-safety-net` (retrieval side). Coverage caveat recorded.

## Verdict
Adopt deterministic-content ids + insert-before-prune with an enumerated stale set and per-stage failure degradation; adapt the 10k snapshot bound and doc-store query shape to your backend; omit nothing — this is the portable crash-safety ordering itself.
