<!-- capsule-v2 -->
# Add/search pipeline — the V3 phased batch flow

**Source:** mem0 MIT `<branch>@<commit>`; Codebase Memory `mem0`. **Question:** how does a memory `add` extract facts and store them, and `search` retrieve them, in the shipped V3 phased batch pipeline?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py` (3,856 lines; sync+async twins): `_build_filters_and_metadata` (:314-420), `add` (:760-880), `_add_to_vector_store` (:881-1050), `search` (:3031-3130), `_validate_search_params` (:212), `_validate_and_trim_search_query` (:239).
**Signature:** `add(messages, ...)` — V3 PHASED BATCH: ADDITIVE extraction in one LLM call (not the classic per-fact ADD/UPDATE/DELETE loop); then embeds, scopes, and stores; `search(query, ...)` — validates, embeds, filters, and retrieves top-k.
**Data Shape:** `MemoryConfig` chain drives providers (embedding/llm/vector_store); `_build_filters_and_metadata` returns `base_metadata_template` (what's stored) + `effective_query_filters` (what's queried); identity keys `user_id`/`agent_id`/`run_id`.

### Decisive source
```ts
# V3 PHASED BATCH: additive extraction in one LLM call
# _build_filters_and_metadata returns TWO dicts:
#   base_metadata_template (stored): identity keys set ONLY from entity params,
#     same keys STRIPPED from caller metadata (issue #6655 — freeform metadata
#     could place a memory into a scope the caller never passed)
#   effective_query_filters (queried): adds resolved actor (arg -> filters)
# search validates threshold/top_k BEFORE defaults; trims the query
```

**Flow:** `add` batches messages → one additive LLM extraction → embed → scope (via `_build_filters_and_metadata`) → store to the vector store + entity store + SQLite history. `search` validates params (reject-don't-default), trims the query, embeds, applies filters, retrieves top-k.
**Invariant:** identity scope is re-built, never trusted (freeform metadata can't place a memory into an un-passed scope); validation happens before defaults so invalid explicit values can't hide; additive extraction in one call.
**Probe:** `tests/memory/` + `tests/test_memory.py` (add stores + links entities; search respects filters + threshold; scope enforced).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "Memory add search pipeline extraction scope filters batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the V3 phased batch add/search pipeline (additive extraction, re-built scope, validate-before-defaults); adapt the providers and batch size to host.
