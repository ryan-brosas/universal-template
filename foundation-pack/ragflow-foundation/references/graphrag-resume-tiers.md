<!-- capsule-v2 -->
# GraphRAG three-tier resume — how does a crashed/cancelled KB indexing run avoid redoing paid LLM work?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** Where must a porter persist progress so that resume skips finished work at doc, unit-of-work, and whole-phase granularity without stale results?

## Three durability tiers in one pipeline
**Path/Symbol:** `rag/graphrag/checkpoints.py` (whole file); `rag/graphrag/phase_markers.py` (whole file); `rag/graphrag/general/index.py:load_subgraph_from_store` (:209-253) + marker invalidation (`run_graphrag_for_kb`, :524-531).
**Signature:** `async def save_checkpoint(tenant_id: str, kb_id: str, checkpoint_type: str, checkpoint_key: str, payload: Any) -> bool`; `async def load_checkpoints(tenant_id, kb_id, checkpoint_type, *, page_size=None) -> dict`; `def has_phase_marker(kb_id: str, phase: str) -> bool`.
**Data Shape:** Tier A (doc): subgraph serialized as node-link JSON into a doc-store chunk with `knowledge_graph_kwd="subgraph"`; reloaded by one query conditioned `{knowledge_graph_kwd:["subgraph"], removed_kwd:"N", source_id:[doc_id]}` offset 0 limit 1. Tier B (unit of work): Redis data key `graphrag:checkpoint:{tenant}:{kb}:{type}:{sha256-key}` plus SET index `...:keys`, both TTL 7d; save is a transactional pipeline (SET+SADD+EXPIRE). Tier C (phase): Redis string `graphrag:phase:{kb_id}:resolution_done|community_done`, TTL 7d, deliberately KB-scoped not task-scoped.

### Decisive source
```python
# checkpoints.py — content-addressed identity + atomic index/data commit
def stable_checkpoint_key(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

pipeline = redis_client.pipeline(transaction=True)
pipeline.set(data_key, json.dumps(payload, ensure_ascii=False), ex=CHECKPOINT_TTL_SECONDS)
pipeline.sadd(index_key, checkpoint_key)
pipeline.expire(index_key, CHECKPOINT_TTL_SECONDS)
```
```python
# phase_markers.py — coarse markers survive task cancellation by design
# "Markers are intentionally KB-scoped (not task-scoped) so they survive
#  task cancellation and the creation of a new task on resume."
# run_graphrag_for_kb after ANY successful merge:
clear_phase_markers(kb_id)   # merged graph changed ⇒ resolution/community stale
resolution_pending = with_resolution
community_pending = with_community
```

**Flow:** build_one checks tier A (`load_subgraph_from_store`) before LLM extraction → resolution/community loops consult tier B dicts passed in and replay hits instead of calling the LLM → `run_graphrag_for_kb` consults tier C to skip whole phases even when no new docs arrived (pure-resume loads the persisted graph via `get_graph`) → any successful merge clears tier C so downstream phases rerun.
**Invariant:** Checkpoint identity is content-addressed (sorted nodes / normalized pairs), never positional; a phase marker may only be set AFTER the phase's result is fully persisted; Redis failure degrades to "work again", never to "skip work" (`has_phase_marker` returns False on error).
**Probe:** `test/unit_test/rag/graphrag/test_checkpoints.py` pins stable keys under member reorder (`["B","A"]` == `["A","B"]`), atomic no-partial-state on pipeline failure, tenant/kb scoping; `test_phase_markers.py` pins kb namespacing and redis-down ⇒ has=False.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "checkpoint resume phase", filePattern: "rag/graphrag/*", fields: ["signature","lines"] });   // rank-1..12 all checkpoints/phase_markers symbols
await mcp.codebase_memory.trace_path({ project: "ragflow", function_name: "save_checkpoint", direction: "inbound" });   // callers: entity_resolution, community_reports_extractor, general/index
await mcp.codebase_memory.trace_path({ project: "ragflow", function_name: "has_phase_marker", direction: "inbound" });  // callers: run_graphrag_for_kb, do_handle_task, TaskHandler._run_graphrag
```

## Verdict
Adopt the three-tier split (per-doc artifact, content-addressed unit checkpoints, coarse phase flags) and the merge-clears-markers invalidation rule; adapt storage (Redis/doc store) to host primitives keeping MULTI-atomicity for index+data; omit the specific TTLs and key prefixes if the host has its own expiry story. Coverage caveat: `test/unit_test/rag/graphrag/test_checkpoint_resume.py` is entirely commented out at this pin — it executes zero tests; resume behavior is evidenced only by active tests + source.
