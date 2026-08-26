<!-- capsule-v2 -->
# ChromaDB where-clause grammar — how do multi-operator and negated filters survive a backend that allows one operator per field?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mnt-hdd-utopia-inspo-memory-mem0`. **Question:** how is the universal op-dict filter compiled into ChromaDB's restrictive where grammar without silently dropping bounds or erasing NOT clauses?

## Connected graph-selected seam
**Path/Symbol:** `mem0/vector_stores/chroma.py`: `ChromaDB._generate_where_clause` (staticmethod, :254-364) with `op_map`, `negate_map`, `convert_condition`, `combine`.
**Signature:** `_generate_where_clause(where: Optional[dict]) -> Optional[dict]` — None in, None out; dict-in → Chroma-native where tree.
**Data Shape:** accepts the universal intermediate (per-key op-dicts, `$or` list-of-dicts, `$not` list-of-dicts, `"*"` wildcard, scalars). ChromaDB's grammar: each dict level may hold exactly ONE field OR ONE logical operator; a field expression may carry exactly ONE operator.

### Decisive source
```python
# One clause per operator: ChromaDB rejects field expressions
# with more than one operator, so a range like {"gte": 18, "lte": 65}
# must become two clauses combined with $and by the caller (previously
# each operator overwrote the last, silently dropping bounds).
return [{key: {op_map.get(op, "$eq"): val}} for op, val in value.items()]
...
# NOT(a AND b) == (NOT a) OR (NOT b)
combined = combine(negated_fields, "$or")
...
negated_fields.append({sub_key: {negate_map.get(op, "$ne"): val}})
```

**Flow:** top-level walk → `$or`: per-branch fields compiled then AND-combined inside the branch, branches OR-combined → `$not`: each field/op pair inverted via negate_map (gt→lte, gte→lt, lt→gte, lte→gt, in↔nin, eq↔ne), inverted pairs joined `$or` (De Morgan), groups joined `$and` → plain keys: wildcard returns NO clause (Chroma has no existence operator), op-dicts become one single-op clause PER OPERATOR, scalars become `$eq` → final combine unwraps singletons so one condition stays a bare `{key: {op: val}}`.
**Invariant:** two regression classes are pinned upstream and MUST survive any port — (1) same-field ranges keep BOTH bounds as separate `$and`-joined clauses (the old code built one dict where the second operator overwrote the first, so `{"gte": 18, "lte": 65}` degraded to `$lte: 65` returning explicitly-excluded rows); (2) operators missing from negate_map fall back to `$ne` instead of vanishing (unknown ops were previously dropped from $not, which could erase the entire NOT clause and return unfiltered results). contains/icontains have no substring operator in Chroma: they fall back to equality positive-path and inequality under negation.
**Probe:** `grep -n "negate_map" mem0/vector_stores/chroma.py` (:284 map def + :346 fallback use); `grep -c '"\$and"' mem0/vector_stores/chroma.py`.
**Direct test:** `tests/vector_stores/test_chroma.py::test_generate_where_clause_same_field_range_keeps_both_bounds` (:349), `..._or_with_same_field_range` (:361), `..._or_with_multi_field_condition` (:372), `..._not_contains_negates_instead_of_vanishing` (:384) — all four regression docstrings name the old silent-drop behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "_generate_where_clause ChromaDB where clause", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split-per-operator + De-Morgan-negation + singleton-unwrap shape whenever a backend restricts expressions to one operator/field; adapt op_map/negate_map to the target's operator names; omitting either regression fix reintroduces documented data-return bugs. Fully direct-tested at this pin (no caveat).
