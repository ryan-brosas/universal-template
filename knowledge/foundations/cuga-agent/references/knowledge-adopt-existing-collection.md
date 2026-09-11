<!-- capsule-v2 -->
# Adopt-existing-collection gate — when may a config PATCH silently repoint retrieval at an already-built collection, and why only on an EMPTY current KB?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** After applying a knowledge config whose embedder maps to a collection that was already built and populated, how does the active-collection pointer move WITHOUT a reindex — and what guard prevents stealing documents from a non-empty KB?

## Pointer adoption only when target is populated AND current is empty
**Path/Symbol:** `src/cuga/backend/server/manage_routes/knowledge_routes.py:559-622` (adopt block inside `patch_draft_knowledge`, post-apply); collection naming `kb_agent_{sanitized_agent_id}_{vector_config_hash}`.
**Signature:** runs after live apply while still holding `agent_draft_lock`; condition: `live_engine._reindex_in_progress` empty AND `_adopt_hash != _cur_hash`.
**Data Shape:** On adopt: `app_state.knowledge_config_hash = _adopt_hash`, `persist_active_vector_config(agent_id, engine, hash)` (survives restart), response flags `adopted_existing_collection=True` + `active_document_count=N` + `reindex_recommended=False`. On non-adopt: pointer untouched, log explains "requires a Re-index".

### Decisive source
```python
# knowledge_routes.py:585-603 (condensed)
_existing_docs = await live_engine.list_documents(_adopt_coll)
if _existing_docs:
    # Only adopt (silently repoint retrieval at the target) when
    # the CURRENT KB is EMPTY -- the import / fresh-agent case,
    # where the target holds the config's documents and there is
    # nothing to lose. When the current KB is NON-EMPTY, a draft
    # embedder / chunk / metric change must NOT silently repoint
    # retrieval at a pre-existing collection: it may hold stale /
    # partial / older content ...
    _cur_coll = f"{_adopt_base}_{_cur_hash}" if _cur_hash else _adopt_base
    _current_docs = await live_engine.list_documents(_cur_coll)
    if not _current_docs:
        live_state.knowledge_config_hash = _adopt_hash
```
The bug this closes ("imported config, no documents"): the active pointer stayed on the OLD collection's hash after applying a config whose embedder maps to an ALREADY-BUILT collection, so users saw zero documents. Each collection carries its OWN pinned embedder (`_resolve_embeddings_for_collection`), so retrieval from either collection stays correct — adoption is purely about which hash the pointer names.

**Flow:** apply config → compute `_adopt_base`/`_adopt_coll` from sanitized agent id + new vector_config_hash → if no reindex in flight and hash differs → list target docs → if populated AND current KB empty → flip pointer + persist + clear reindex banner; else log non-adoption reason → whole check wrapped in try/except that NEVER breaks the PATCH (`# noqa: BLE001 — never break the PATCH`).
**Invariant:** Adoption requires BOTH sides of the emptiness test: target populated (proves the vectors exist) AND current empty (nothing lost). A non-empty current KB must always take the explicit Re-index path, because the metadata schema has no content hash to prove the old collection matches the user's CURRENT docs. Never flip while a reindex is in flight — the deferred flip owns the pointer then.

**Probe:** `tests/unit/test_knowledge_reindex_in_progress_guard.py` (in-flight guard + publish/flip interplay), `tests/unit/test_knowledge_publish_import_pipeline.py` (import path where adoption fires).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "patch_draft_knowledge adopted_existing_collection persist_active_vector_config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-sided emptiness gate whenever config changes can map to pre-built vector stores. Adapt collection naming/hash scheme. Omit the persistence step if your pointer lives only in memory. Coverage caveat: no unit test drives the adopt branch directly at HEAD; behavior verified by source read + adjacent reindex-guard tests.
