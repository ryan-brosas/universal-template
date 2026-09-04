<!-- capsule-v2 -->
# LanceDB filter compiler — how does a shared expression tree become safe backend SQL, and where does string interpolation stay acceptable?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** how is FilterExpr compiled to a LanceDB WHERE clause and what are the operator-translation traps (contains→LIKE, exists→IS NULL)?

## recursive match-based compiler
**Path/Symbol:** `packages/graphrag-vectors/graphrag_vectors/lancedb.py` (`_compile_filter` :139-155, `_compile_condition` :157-194, application point `similarity_search_by_vector` :211-212).
**Signature:** `_compile_filter(expr: FilterExpr) -> str`; applied as `query = query.where(self._compile_filter(filters), prefilter=True)`.
**Data Shape:** output is a single SQL string; AND/OR children parenthesized per-part (`" AND ".join(f"({p})")`), NOT wrapped at top level.

### Decisive source
```python
# lancedb.py:184-191 — semantic operators degrade to LIKE/NULL idioms;
# contains/startswith/endswith interpolate the value INTO the pattern with
# NO escaping of % or _ — user values containing wildcards change semantics
case Operator.contains:
    return f"{field} LIKE '%{value}%'"
...
case Operator.exists:
    return f"{field} IS NOT NULL" if value else f"{field} IS NULL"
```
```python
# :162-163 — quoting rule is type-based only; strings single-quoted,
# everything else str()'d raw (numbers fine, datetimes need pre-formatting)
def quote(v): return f"'{v}'" if isinstance(v, str) else str(v)
```

**Flow:** `similarity_search_by_vector(embedding, filters=F.year >= 2024)` → compile tree depth-first via structural match on Condition/AndExpr/OrExpr/NotExpr → `.where(sql, prefilter=True)` so filtering happens BEFORE ANN ranking (post-filter would shrink k unpredictably) → results mapped back to VectorStoreDocuments.
**Invariant:** unknown node types and unsupported operators raise ValueError LOUDLY (:153-155, :192-194) — a compiler that silently drops filters returns wrong result SETS, the worst failure mode for filtered retrieval; every backend in graphrag-vectors implements its OWN compiler over the same tree (cosmosdb.py :209-246), so new operators require touching every backend or adding a default-refusing arm.
**Probe:** no direct unit suite for the compiler (LanceDB backend needs the optional dependency); pinned by source greps — `grep -c 'IS NOT NULL' lancedb.py` = 1, `grep -c 'LIKE' lancedb.py` = 3, `grep -c 'prefilter=True' lancedb.py` = 2 @pin. Recorded caveat: compile behavior verified by source read + client-side algebra tests (test_filtering.py), not executed against live LanceDB.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "compile filter condition LanceDB where clause", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the recursive structural-match compiler shape + loud refusal on unknown nodes + prefilter-before-rank ordering; adapt target dialect; if porting contains/startswith verbatim, ADD wildcard escaping (upstream accepts the interpolation risk because filter values are pipeline-controlled).
