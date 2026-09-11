<!-- capsule-v2 -->
# Query-context normalization contract — how do heterogeneous context payloads become a stable API response shape?

**Source:** graphrag (MIT) `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory project `graphrag`. **Question:** How does GraphRAG guarantee every search mode returns the same five-key context skeleton regardless of which builders ran?

## reformat_context_data + get_embedding_store — response shaping at the API edge
**Path/Symbol:** `packages/graphrag/graphrag/utils/api.py`: `reformat_context_data` (:26-54), `get_embedding_store` (:15-23).
**Signature:** `reformat_context_data(context_data: dict) -> dict`; `get_embedding_store(config: VectorStoreConfig, embedding_name: str) -> VectorStore`.
**Data Shape:** input values are DataFrames, dicts, or nothing-safe; output maps the FIXED five keys `reports|entities|relationships|claims|sources` to lists of row-dicts (DataFrame `.to_dict(orient="records")`), plus any extra keys.

### Decisive source
```python
final_format = {"reports": [], "entities": [], "relationships": [], "claims": [], "sources": []}
for key in context_data:
    records = (context_data[key].to_dict(orient="records")
               if context_data[key] is not None and not isinstance(context_data[key], dict)
               else context_data[key])
    if len(records) < 1:
        continue                    # empty DataFrame → default [] survives
    final_format[key] = records     # dicts pass through UNTOUCHED; unknown keys get ADDED
return final_format
```

**Flow:** mode-specific context builders emit whatever they have → this single reformatter runs at the API edge (query-api-surface plane) → consumers can rely on the five-key skeleton. `get_embedding_store` resolves one vector store from config's `index_schema[embedding_name]` and connects it.
**Invariant:** the five defaults are always present (missing modes stay `[]`); dict-valued entries bypass record conversion (already-shaped payloads survive verbatim); unknown non-empty keys are APPENDED to the output, not dropped. TRAPS probed byte-exact: a `None` value reaches `len(None)` and raises RAW TypeError — callers must filter nulls first; an EMPTY DataFrame yields `[]` (skip branch), not an error.
**Probe:** no dedicated unit test (tests/unit/utils covers encoding only — recorded caveat). Deterministic probe EXECUTED pre-write via lane venv: `{entities: 2-row DF, reports: empty DF, extra_key: 1-row DF, claims: dict}` → `{'claims': ('dict',1), 'entities': ('list',2), 'extra_key': ('list',1), 'relationships': ('list',0), 'reports': ('list',0), 'sources': ('list',0)}`; `{'bad': None}` → `TypeError('object of type NoneType has no len()')`.

## Get live surrounding code
**Retrieve:** (executed live; rank-line-exact)
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "reformat_context_data context records reports entities", limit: 10 });
// rank#1 graphrag.packages.graphrag.graphrag.utils.api.reformat_context_data :26-54
```

## Verdict
Adopt the fixed-defaults skeleton plus pass-through-unknowns policy as the stable public response shape across retrieval modes. Adapt key names and record conversion to host payload types — but port the None-guard explicitly (upstream lacks it). Omit get_embedding_store unless wiring graphrag_vectors-style schema-indexed stores.
