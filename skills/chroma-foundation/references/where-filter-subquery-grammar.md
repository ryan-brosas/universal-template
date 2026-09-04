<!-- capsule-v2 -->
# Where-filter subquery grammar — How does a JSON where-filter compile to SQL that matches per-key EAV rows?

**Source:** Chroma Apache-2.0 `main@93652ec0869489b803fe1682427fc02bd47bec14`; Codebase Memory `ext-chroma`. **Question:** Metadata is stored as one row per (embedding, key) with typed value columns — how must `$eq/$ne/$gt/$gte/$lt/$lte/$in/$nin` compile so multi-row semantics stay correct?

## _where_clause / _value_criterion
**Path/Symbol:** `chromadb/segment/impl/metadata/sqlite.py:_where_clause` (:650-675), `_value_criterion` (:678-723); recursion entry `_where_map_criterion` (:521-544) folds `$and`/`$or` lists with reduce(&)/reduce(|).
**Signature:** `_value_criterion(key, value, op, metadata_q, metadata_t, embeddings_t) -> Criterion`; builds `sub_q = metadata_q.where(metadata_t.key == ParameterValue(key))` then wraps membership.
**Data Shape:** `embedding_metadata(id, key, string_value, int_value, float_value, bool_value)` — exactly one of the value columns is non-null per row; numeric check excludes bool explicitly (`is_numeric = not isinstance(obj,bool) and isinstance(obj,(int,float))`) because Python bools are ints.

### Decisive source
```python
if is_numeric(value) or (isinstance(value, list) and is_numeric(value[0])):
    int_col, float_col = metadata_t.int_value, metadata_t.float_value
    if op in ("$eq", "$ne"):
        expr = (int_col == p_val) | (float_col == p_val)
    elif op == "$gt":
        expr = (int_col > p_val) | (float_col > p_val)
    ...  # $gte/$lt/$lte same OR-pair shape
    else:
        expr = int_col.isin(p_val) | float_col.isin(p_val)
else:
    if isinstance(value, bool) or (isinstance(value, list) and isinstance(value[0], bool)):
        col = metadata_t.bool_value
    else:
        col = metadata_t.string_value
    if op in ("$eq", "$ne"):
        expr = col == p_val
    else:
        expr = col.isin(p_val)

if op in ("$ne", "$nin"):
    return embeddings_t.id.notin(sub_q.where(expr))
else:
    return embeddings_t.id.isin(sub_q.where(expr))
```

**Flow (live-verified against real pypika output):** every leaf becomes `embeddings.id [NOT] IN (SELECT … WHERE key=? AND <typed predicate>)`; numeric predicates OR the int/float columns; `$ne`/`$nin` invert **membership in the matching-ID set**, not individual rows — this is what makes "no row for this ID has value red" correct under EAV layout. A literal value short-circuits into `{"$eq": value}`. `$and`/`$or` recurse over nested Where dicts; top-level keys AND together.
**Invariant:** The inner subquery constrains `key` on EVERY arm; forgetting it (or inverting by row negation like `NOT(expr)`) breaks $ne across an ID's multiple metadata rows.
**Probe:** `/tmp/chroma-p1/probe_battery.py` mq.* checks incl live criterion builds asserting parameterized `key=?`, `NOT IN`, dual-column OR-pairs, member-lists (all GREEN). Upstream: `chromadb/test/segment/impl/metadata/test_metadata.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-chroma", query: "_where_clause _value_criterion nin ne notin", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the NOT-IN-subquery grammar for any EAV-style filter compiler (mem0's pgvector adapter uses the same shape); adapt column names/type dispatch to your schema; omit pypika specifics if your builder composes criteria differently — keep only the operator-to-membership mapping.
