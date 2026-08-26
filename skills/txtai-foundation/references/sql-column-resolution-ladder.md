<!-- capsule-v2 -->
# SQL column resolution ladder — how a user column name becomes a real expression across SQL dialects

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How does a query referencing an arbitrary document field resolve to valid SQL without knowing the backend's JSON syntax?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/rdbms.py:RDBMS.resolve` (:132-163), `.query` (:177-243), `.defaults` (:522-530); dialect hooks `embedded.py:jsonprefix/jsoncolumn` (:57-63), `duckdb.py` twins (:67-73); error wrapper `base.py:Database.execute` (:310-328).
**Signature:** `resolve(name, alias=None) -> str`; `query(query, limit, parameters, indexids)`.
**Data Shape:** standard section cols `["indexid", "id", "tags", "entry"]`; bare cols `["data", "object", "score", "text"]`; everything else is a dynamic documents.data JSON path.

### Decisive source
```python
# Use JOIN when documents table is used to utilize indexes, default to LEFT JOIN
join = "JOIN" if any(x and self.jsonprefix() in x for x in [where, groupby, orderby]) else "LEFT JOIN"
```
```python
# Standard columns - need prefixes
if name.lower() in sections:
    return f"s.{name}"
# Standard columns - no prefixes
if name.lower() in noprefix:
    return name
# Other columns come from documents.data JSON
return self.jsoncolumn(name)
```

**Flow (resolve ladder):** explicit alias → skip if identical/standard else `name as "alias"` → configured expressions map wins → already-resolved names pass through (start with jsonprefix or equal `s.<col>`) → section columns get `s.` prefix → text/score/data/object stay bare → unknown names become `json_extract(data, '$.<name>')` (SQLite) or `json_extract_string(...)` (DuckDB).

**Flow (parser-side pre-ladder, pass-2 addition):** before any name reaches this ladder it passes through `Expression.resolve` (`src/python/txtai/database/sql/expression.py:397-413`), which REFUSES to resolve tokens whose normalized form is a registered SELECT alias or that start with `:` (bind parameter) — see `select-alias-suppression`. The ladder is also fed at CONFIGURE time: `Database.registerexpressions` (`database/base.py:290-308`) pre-parses each configured expression via `self.sql.snippet(expression)`, so `columns.expressions` entries arrive at RDBMS.resolve already in resolved SQL form.

**Flow (query assembly):** select defaults to `s.id, text, score`; indexids mode forces `s.indexid, score`; JOIN-vs-LEFT-JOIN chosen by jsonprefix presence in where/groupby/orderby (dynamic JSON predicates can't use LEFT-JOIN short-circuit); default `ORDER BY score DESC` only when similarity exists and user gave no orderby; LIMIT/OFFSET appended from clause-or-call values; results map columns by cursor.description keeping the FIRST NON-None value on duplicate names; object column decoded through encoder.

**Invariant:** Every dialect difference must hide behind `jsonprefix()`/`jsoncolumn()` — the ladder itself is dialect-free; adding a fourth branch that emits backend-specific syntax outside those two hooks breaks custom backends. User SQL executes through `execute()`, which converts ANY backend exception into SQLError (`raise ... from None`) — porters relying on native exception types lose them. Named bind parameters are passed through on SQLite but rewritten positionally by DuckDB's formatargs.

**Probe:** `test/python/testdatabase/testrdbms.py:testSQL` (:657-697 — json field `attribute = 'ID4'`, count(*), data/entry projection, SQLError raised on bad SQL :696-697), `testSettings` (:641-655).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "resolve jsoncolumn jsonprefix query join score desc", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: hits rank RDBMS.query/resolve family line-exact.

## Verdict
Adopt the ordered resolution ladder + dialect-hook isolation + first-non-None duplicate-column rule + the parser-side alias/`:`-bind suppression gate that precedes it; adapt JSON functions per backend; omit expression indexes (`expressions` config + createindexes) until users need indexed computed columns. Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z; pass-2 addition source-read at expression.py:397-413 and database/base.py:290-308, same pin.
