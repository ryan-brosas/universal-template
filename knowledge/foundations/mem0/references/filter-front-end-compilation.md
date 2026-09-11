<!-- capsule-v2 -->
# Filter merge front-end — how do platform AND/OR/NOT filters compile to a universal intermediate without losing conditions?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mem0`. **Question:** how does the memory layer normalize an operator filter dialect into per-key op-dicts that every vector-store translator can consume — and where do conditions get silently merged?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py` `Memory._process_metadata_filters` (:1524-1599) + nested `process_condition` (:1536-1557) and `merge_filters` (:1559-1565); async twin :3189-3264; consumer: each backend's filter translator (mined twin: `qdrant-filter-translation.md`). TS mirror `mem0-ts/src/oss/src/memory/index.ts :2098-2198`.
**Signature:** `_process_metadata_filters(metadata_filters: Dict) -> Dict`; `process_condition(key, condition) -> Dict[str, Dict]` (one key → `{key: {op: value}}`); `merge_filters(target, source) -> None` (in-place).
**Data Shape:** input keys: leaf field names (scalar or `{op: value}`), `"AND"`/`"OR"`/`"NOT"` lists, wildcard scalar `"*"`; output: flat dict of `{field: {op: val}}` plus `$or`/`$not` list keys; operator vocabulary exactly eq/ne/gt/gte/lt/lte/in/nin/contains/icontains.

### Decisive source
```python
if operator in operator_map:
    result.setdefault(key, {})[operator_map[operator]] = value
else:
    raise ValueError(f"Unsupported metadata filter operator: {operator}")
...
def merge_filters(target, source):
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            target[key].update(value)     # ← same-field multi-op: ne+gt MERGE into one dict
        else:
            target[key] = value            # ← non-dict collision REPLACES silently
...
elif key == "AND":
    if not isinstance(value, list): raise ValueError("AND operator requires a list of conditions")
    for condition in value:
        for sub_key, sub_value in condition.items():
            merge_filters(processed_filters, process_condition(sub_key, sub_value))
```

**Flow:** walk top-level keys → AND-list members are deep-merged one-by-one INTO the top-level processed dict (AND is expressed by accumulation, not nesting) → OR/NOT members are each compiled standalone then appended to `$or`/`$not` lists (empty or non-list → ValueError) → plain leaves go through `process_condition`: non-dict values become equality (with `"*"` wildcard passthrough), dicts map through the fixed 10-operator table with loud refusal on unknown ops.
**Invariant:** AND = merge-accumulate at TOP level (a port that nests it under `$and` changes semantics for backends reading only top-level keys — though note the qdrant translator ALSO accepts literal `$and`, so the two encodings coexist upstream); same-field collisions inside AND merge only when BOTH sides are op-dicts and REPLACE otherwise — order-dependent, so conflicting scalars last-write-win by design; unknown operators fail LOUD (ValueError) rather than degrading to equality.
**Probe:** no dedicated unit suite for `_process_metadata_filters` at this HEAD — coverage caveat; behavior is pinned indirectly via `tests/vector_stores/test_qdrant.py::test_search_with_filters` family consuming its output, and the qdrant capsule's `$or/$not` dual-key dedup trap documents the downstream contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_process_metadata_filters merge_filters process_condition AND OR NOT", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: mnt-hdd-utopia-inspo-memory-mem0.mem0.memory.main.Memory._process_metadata_filters Method mem0/memory/main.py 1524-1599)

## Verdict
Adopt the compile-to-intermediate shape with loud unknown-operator refusal; adapt the operator set to your store's native grammar; omit the wildcard passthrough only if your translator has first-class match-all.
