<!-- capsule-v2 -->
# Node attribute preservation — what must the untyped extraction path return so it never wipes typed attributes?

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `graphiti`. **Question:** `extract_attributes_from_nodes` assigns `node.attributes = attributes` wholesale — what contract must the per-node extractor satisfy so an untyped pass cannot clear attributes a previous typed pass stored?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/maintenance/node_operations.py`: `extract_attributes_from_nodes` (:726-780; type-resolution expression :752, assignment comment :762, assignment loop :764-766), `_extract_entity_attributes` (:783-830; no-type early return :794, overlay merge :822, validation-only discard :831).
**Signature:** `async def _extract_entity_attributes(llm_client, node: EntityNode, episode, previous_episodes, entity_type: type[BaseModel] | None) -> dict[str, Any]`
**Data Shape:** `entity_types: dict[label → type[BaseModel]] | None`; per-node lookup key = first label that isn't `'Entity'`, else `''` (:752) — resolves to `None` both when `entity_types is None` AND when the node's label is missing from the map. Return value is the ALREADY-MERGED attribute dict; the caller assigns it wholesale.

### Decisive source
```python
if entity_type is None or len(entity_type.model_fields) == 0:
    # No applicable type means nothing to extract, not "extracted nothing": return the
    # node's prior attributes so the caller's assignment leaves them untouched. Returning
    # {} here would clear attributes a previous typed pass stored on a deduplicated node.
    return dict(node.attributes or {})
...
merged, _ = apply_capped_attributes(llm_response, entity_type, node.attributes,
                                    merge_mode='overlay', ...)
# Shape validation only — we discard the validated instance because returning
# `model_dump()` would expand defaults across all fields and clobber prior
# values that the merge above just preserved.
entity_type(**merged)
return merged
```

**Flow:** resolve per-node type → no applicable type ⇒ return a **copy** of prior attributes (typed path never entered, zero LLM calls) → otherwise LLM extraction → `apply_capped_attributes(..., merge_mode='overlay')` overlays extracted fields ONTO prior values → validate shape, discard instance → return merged → caller does `node.attributes = attributes`.
**Invariant:** "no applicable type" ≠ "extracted nothing" — the early return must hand back prior attributes (`dict(node.attributes or {})`, never `{}` and never an alias of the node's own dict). Two distinct routes used to hit the wiped-`{}` bug: (1) `entity_types=None` on a later episode for a node hydrated from the DB, (2) label absent from the supplied map (Entity-only nodes take the `''` key). The typed path preserves via `merge_mode='overlay'` (edge attributes use `'replace'` — different mode, don't unify them); the validation-discard exists because `model_dump()` expands pydantic defaults and would clobber exactly the values the merge preserved. Wholesale assignment IS the merge: no call-site guard needed, matching `add_triplet`'s documented merge-not-replace rule.
**Probe:** `tests/utils/maintenance/test_node_operations.py:924` (`..._when_entity_types_none`) and `:956` (`..._when_label_not_in_entity_types`) — `{'age': 30, 'city': 'New York'}` survives verbatim through an untyped pass. EXECUTED under repo `.venv`: 2 passed at `993e081a`; RED (both fail, attributes become `{}`) with pre-fix `node_operations.py` from `401c59a6`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "extract_attributes_from_nodes entity type attributes", limit: 10, fields: ["signature", "name", "file"] });
// → node_operations.extract_attributes_from_nodes :726-780 + _extract_entity_attributes :783-830
// Same twin-graph note as edge-ce-shortlist-rrf-fusion.md: path-slugged project is
// FRESH @993e081a; short-name "graphiti" is STUCK pre-drift (@401c59a).
```

## Verdict
Adopt the prior-preserving early return plus the validation-only-discard idiom (validate without `model_dump()`); adapt the label-resolution expression to your node taxonomy; omit the prompt/context plumbing around it. Coverage caveat: none for the unit-level contract — both direct tests run in default CI (no DB fixture needed); note upstream's DB-backed `add_triplet` preservation test parametrizes to zero drivers when backends are disabled, so it does NOT run in default CI (stated in the fix narrative).
