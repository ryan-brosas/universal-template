<!-- capsule-v2 -->
# Search validation — reject-don't-default

**Source:** mem0 MIT `<branch>@<commit>`; Codebase Memory `mem0`. **Question:** how does a memory `search` validate its inputs so bad params can't hide behind defaults and the query is safe?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `search` (:3031-3130), `_reject_top_level_entity_params` (:165), `_validate_search_params` (:212), `_validate_and_trim_search_query` (:239), `_process_metadata_filters`.
**Signature:** `search(query, ...)` — validates `threshold`/`top_k` BEFORE defaults, trims the query, rejects top-level entity kwargs (the `filters=` dict is mandatory), processes metadata filters.
**Data Shape:** `threshold` (float) and `top_k` (int) validated; query trimmed (whitespace collapse); entity ids inside filters individually validated + trimmed.

### Decisive source
```ts
# Reject-don't-default validation:
# - Top-level entity kwargs are REJECTED (_reject_top_level_entity_params) — filters= is mandatory
# - threshold and top_k are validated BEFORE defaults, so invalid explicit values can't hide behind defaults
# - Entity ids inside filters are individually validated and trimmed
# - query is trimmed (_validate_and_trim_search_query)
```

**Flow:** search validates its inputs up front: top-level entity kwargs rejected (filters mandatory), threshold/top_k validated before defaults, entity ids validated + trimmed, the query trimmed, then metadata filters processed and retrieval runs.
**Invariant:** invalid explicit values can't hide behind defaults (validated before defaults applied); the query is trimmed; filters are the only way to scope.
**Probe:** `tests/memory/` search tests (invalid threshold/top_k rejected; top-level entity kwargs rejected; query trimmed; entity id validation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "search validate threshold top_k reject entity params trim query", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reject-don't-default search validation (validate before defaults, reject top-level entity kwargs, trim query/ids); adapt the validation rules to host.
