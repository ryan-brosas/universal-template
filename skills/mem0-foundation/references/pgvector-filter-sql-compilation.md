<!-- capsule-v2 -->
# PGVector filter→SQL compilation — how do universal operator filters become parameterized SQL without injection or silent coercion?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how does a processed filter dict compile to a WHERE fragment over a JSONB payload column, and which coercions happen where?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/pgvector.py`: module-level `OPERATOR_SQL_MAP` (:36-47) + `_build_filter_conditions(filters)` (:50-119).
**Signature:** `_build_filter_conditions(filters: Optional[dict]) -> tuple[list[str], list]` — returns (SQL fragments joined with AND, flat positional params).
**Data Shape:** input is the universal per-key op-dict intermediate produced by the platform front-end (`{"key": {"gte": 1}}`, `$or: [dict]`, `$not: [dict]`, scalar equality, `"*"` wildcard). Params are ordered key,value pairs appended in fragment order — callers splice `*filter_params` between vector/top_k positionally.

### Decisive source
```python
OPERATOR_SQL_MAP = {
    "eq": ("payload->>%s = %s", False),
    ...
    "gt": ("(payload->>%s)::numeric > %s", True),
}
...
if op in ("in", "nin"):
    if not isinstance(op_value, list):
        raise ValueError(f"Filter operator {op!r} for key {key!r} requires a list value...")
    str_list = [str(v) for v in op_value]
elif op in ("contains", "icontains"):
    escaped = str(op_value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    conditions.append(template + " ESCAPE '\\'")
    params.extend([key, f"%{escaped}%"])
else:
    conditions.append(template)
    if is_numeric:
        params.extend([key, float(op_value)])
    else:
        params.extend([key, str(op_value)])
...
if isinstance(value, bool):
    params.extend([key, json.dumps(value)])   # "true"/"false" — Python str() would emit "True"
```

**Flow:** dict walk → `$or` groups each compiled recursively then AND-joined inside one `(…)` pair, OR-joined together → `$not` compiles each group then emits `NOT (g1 OR g2 …)` (De Morgan over groups) → `"*"` becomes the `?` key-existence operator → op-dict entries dispatch through OPERATOR_SQL_MAP (unknown op ⇒ loud ValueError) → bare scalars become stringified equality (bools JSON-cased first).
**Invariant:** everything user-supplied travels as a bound parameter, never interpolated; numeric comparison casts the TEXT-extracted `payload->>%s` with `::numeric` and coerces via `float()`; `in/nin` stringify members (numbers become strings) and REJECT non-list values loudly because a raw string would iterate characters into a misleading `ANY()` clause; contains/icontains escape `\`, `%`, `_` and append `ESCAPE '\'` — a porter who skips escaping turns user input into a LIKE wildcard.
**Probe:** `grep -n '::numeric' mem0/vector_stores/pgvector.py` (exactly the four numeric-comparison templates :39-42); `grep -c "_ensure_collection()" mem0/vector_stores/pgvector.py` for the sibling seam's 9 guarded entry points.
**Direct test:** `tests/vector_stores/test_pgvector.py::TestBuildFilterConditions` (:2338-2527) pins every operator incl. wildcard escaping (`%50\%\_off%`), boolean JSON casing, numeric-string coercion, and all three loud ValueErrors.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_build_filter_conditions OPERATOR_SQL_MAP pgvector", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the map-driven compilation with param-bound values, `::numeric` casts, LIKE escaping, and loud non-list `in/nin`; adapt table entries to your backend's placeholder style; omit none of the coercions — dropping bool JSON-casing or escaping silently corrupts filters rather than failing. Direct tests cover every arm at this pin (no caveat).
