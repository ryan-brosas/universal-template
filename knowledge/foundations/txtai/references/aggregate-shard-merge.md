<!-- capsule-v2 -->
# Aggregate shard merge — post-hoc GROUP BY/ORDER BY over sharded result lists

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** When one query fans out to sharded indexes, who re-applies aggregate semantics to the merged partial result lists?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/sql/aggregate.py:Aggregate.__call__` (:20-50), `.aggcolumns` (:52-75), `.groupby` (:116-134), `.orderby` (:136-162), `.defaultsort` (:164-179).
**Signature:** `__call__(query, results) -> results`; `Aggregate()` forces `SQL(database=None, tolist=True)` — clause values are LISTS of select expressions, not text.
**Data Shape:** input `results` is a list of per-shard row dicts concatenated; output rows keyed by the ORIGINAL select-column strings (e.g. `"count(*)"`).

### Decisive source
```python
if column.startswith(("count(", "sum(", "total(")):
    aggregates[column] = sum
elif column.startswith("max("):
    aggregates[column] = max
elif column.startswith("min("):
    aggregates[column] = min
elif column.startswith("avg("):
    aggregates[column] = lambda x: sum(x) / len(x)
```
```python
for clause in query["orderby"][::-1]:
    ...
    if clause in query["select"]:
        results = sorted(results, key=operator.itemgetter(clause), reverse=reverse)
```

**Flow:** re-parse the query with the same SQL parser (tolist mode) → detect aggregate columns by RESULT-COLUMN NAME prefix → if groupby present, sort rows by the selected groupby columns (`operator.itemgetter`) then split with `itertools.groupby`; non-aggregate columns repeat the FIRST row's value per group → apply orderby clauses in REVERSE order (stable-sort composition for multi-key ordering), stripping asc/desc and silently skipping columns absent from select → otherwise defaultsort by score desc when a score column exists.

**Invariant:** Aggregation happens on RESULT COLUMN NAMES, not parse-tree functions — any column whose name literally starts with `count(`/`sum(`/`total(`/`max(`/`min(`/`avg(` gets folded; everything else must be a grouping column or it keeps only the first shard's value. Empty shard results are guarded (`"select" in query and results`) before indexing `results[0]` — without that guard an all-shards-empty match raises IndexError (pinned regression).

**Probe:** `test/python/testdatabase/testsql.py:testAggregateEmptyResults` (:28-42 — empty results return `[]`; `count(*)` shards `[{"count(*)": 1}, {"count(*)": 2}]` merge to `[{"count(*)": 3}]`); consumer evidence: `trace_path` inbound on `Aggregate` → `api/base.API.__init__`, `api/cluster.Cluster.__init__`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "aggregate shard partial results groupby orderby defaultsort score merge", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: tier 1 = `Aggregate.defaultsort :164-179`, `.groupby :116-134`, `.orderby :136-162`, `testAggregateEmptyResults :28-42`, `Cluster.shard :185-208`.

## Verdict
Adopt name-prefix aggregate detection + stable reverse-order multi-key sort + first-value repetition for grouping columns + the empty-results guard; adapt the function table (e.g. add median-style folds) to your workload; omit true distributed aggregation — correctness relies on each shard returning raw grouped rows. Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
