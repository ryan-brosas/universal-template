<!-- capsule-v2 -->
# Temp-table similarity join — why similar() results flow through TEMP tables instead of IN-lists

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How do vector search results get injected into a user-authored SQL query, and how do multiple similar() clauses coexist?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/base.py:Database.search` (:143-164); `rdbms.py:RDBMS.embed` (:165-174), `.batch` (:444-459), `.insertbatch` (:469-477), `.scores` (:479-500), `.insertscores` (:510-520); DDL `schema/statement.py:CREATE_BATCH/CREATE_SCORES/IDS_CLAUSE` (:12-33, 98).
**Signature:** `search(query, similarity=None, limit=None, parameters=None, indexids=False)`; `embed(similarity, batch) -> "s.indexid in (SELECT indexid FROM batch WHERE batch=<n>)"`.
**Data Shape:** temp `batch(indexid INTEGER, id TEXT, batch INTEGER)`; temp `scores(indexid INTEGER PRIMARY KEY, score REAL)`.

### Decisive source
```python
if "select" in query and similarity:
    for x in range(len(similarity)):
        token = f"{Token.SIMILAR_TOKEN}{x}"
        if where and token in where:
            where = where.replace(token, self.embed(similarity, x))
elif similarity:
    # Not a SQL query, load similarity results, if any
    where = self.embed(similarity, 0)
```
```python
def batch(self, indexids=None, ids=None, batch=None):
    # Delete batch when batch id is empty or for batch 0
    if not batch:
        self.cursor.execute(Statement.DELETE_BATCH)
    self.insertbatch(indexids, ids, batch)
```

**Flow:** parser emits `<similar_N>` tokens per clause → each replaced by an IDS_CLAUSE subselect over the temp batch table → embed() loads that clause's (indexid|id) rows into `batch` keyed by clause number → first clause (`batch=0`) also clears the table and loads AVERAGED similarity scores into `scores`: every similar() result set contributes `(indexid, score)` pairs merged as `sum(scores)/len(scores)` per indexid → query's SELECT joins `LEFT JOIN scores sc ON s.indexid = sc.indexid`, so `score` is a normal column.

**Invariant:** Clear-on-batch-0 (`if not batch:`) means clause 0 must ALWAYS be loaded before later clauses — reordering embed() calls corrupts the join. Scores are averaged, never maxed: two similar() clauses matching the same row yield the mean. The scores join is LEFT JOIN, so SQL-only queries still work with an empty scores table (query() explicitly clears it when no similarity is present). Deletes reuse the same batch table: three `DELETE ... WHERE id IN (SELECT id FROM batch)` statements over documents/objects/sections.

**Probe:** `test/python/testdatabase/testrdbms.py:testSQL` (:657-697 similar+groupby/having/orderby, similar with limit arg, offset, column filtering), `testSQLBind` (:699-717 bind parameters inside and beside similar()).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "embed batch scores insertscores similarity temporary table", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hit `RDBMS.scores` (:479-500) line-exact.

## Verdict
Adopt temp-table injection for vector results into arbitrary SQL + per-clause batch keys + score averaging; adapt to CTE VALUES lists if your backend lacks temp tables (mind the clear-on-clause-0 ordering); omit multi-clause support only if you also forbid >1 similar(). Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z.
