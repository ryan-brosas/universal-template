<!-- capsule-v2 -->
# Filter-then-search planner (Scan) — how do SQL-filtered queries get their vector candidates sized and joined back?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** When a query mixes SQL filters with `similar(...)` clauses, how many vector candidates must be fetched and how are results joined to the right query?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/embeddings/search/scan.py:Scan.__call__` (:37-77), `Scan.parse` (:79-111), `Scan.default` (:135-151), `Clause.parse` (:177-196); caller `search/base.py:Search.dbsearch` (:210-243).
**Signature:** `Scan(search, limit, weights, index)(queries, parameters)` → list of `(qid, [(id, score)])` sorted by clause uid.
**Data Shape:** parsed queries are dicts (`{"select", "where", "similar": [params], "limit"}`); each `similar` clause is a params list `[text, candidates?, weights?, index?]`.

### Decisive source
```python
multitoken = any(query.get("where") and len(query["where"].split()) > 1 for query in queries)
return self.limit * 10 if multitoken else self.limit
```
```python
for x, result in enumerate(self.search([query.text for query in iqueries], candidates, weights, index)):
    # Save query id and results to later join to original query
    results[iqueries[x].uid] = (iqueries[x].qid, result)

# Sort by query uid and return results
return [result for _, result in sorted(results.items())]
```

**Flow:** parse extracts every `similar()` clause into a `Clause` (uid is GLOBAL across all queries, qid the owning query) → clauses grouped BY target subindex → per group: explicit `candidates` wins, else default = `limit*10` iff ANY query has a multi-token `where` (extra filtering after the index search shrinks the candidate set), else `limit`; same for per-clause `weights` (max wins) → one batched index search per group → `(uid → (qid, results))` dict re-sorted by uid so callers zip by position.

**Invariant:** The uid→qid join is positional-correctness load-bearing: batch search results must never be re-ordered by index name iteration; sorting by uid restores the original per-query order regardless of grouping. Bind parameters (`:name`) are resolved into similar-clause args BEFORE Clause parsing (:113-133) — a porter that resolves them after parsing misroutes string/int/float/index disambiguation (digits→candidates, floats→weights, other strings→subindex names).

**Probe:** `test/python/testembeddings.py:testLimitBindParameter` (:366-380 — `limit :n` bind parameter must not crash the candidate-count parse; str-vs-int guard in `Search.limit`, search/base.py:276-297) plus testdatabase filter suites exercising `similar()` clauses.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Scan clause candidates multitoken bind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 10x-multi-token candidate heuristic + uid/qid two-level join + bind-before-parse ordering; adapt the 10x factor to your filter selectivity; omit subindex routing if you have a single index. Coverage caveat: no dedicated Scan unit file — pinned via embeddings integration tests.
