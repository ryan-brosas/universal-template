<!-- capsule-v2 -->
# SQL dispatch gate — is a user string SQL or a natural-language query?

**Source:** txtai Apache-2.0 `master@a10667a1c2a4721ce719f3648bd1aeedd03dd84a` (9.13.0); Codebase Memory `txtai`. **Question:** How does txtai decide that a user-supplied string is a txtai-SQL statement versus a plain similarity query, and what does a non-SQL string parse into?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/database/sql/base.py:SQL.__call__` (:31-70), `.issql` (:87-105).
**Signature:** `issql(query) -> bool`; `__call__(query) -> {clause: text}`.
**Data Shape:** input is any user string; output is either a 7-key clause dict (`select`, `where`, `groupby`, `having`, `orderby`, `limit`, `offset`, optional `similar`) or the fixed fallback `{"similar": [[query]]}`.

### Decisive source
```python
query = query.lower().strip(";").replace("\n", " ").replace("\t", " ").strip()
# Detect if this is a valid txtai SQL statement
return query.startswith("select ") and (" from txtai " in query or query.endswith(" from txtai"))
```
```python
# Ignore multiple statements
query = query.split(";")[0]
...
# Return clauses, default to full query if this is not a SQL query
return clauses if clauses else {"similar": [[query]]}
```

**Flow:** normalize (lowercase, strip one trailing ";", flatten newlines/tabs) → require prefix `"select "` AND substring `" from txtai "` (or suffix) → if SQL: truncate at first ";" then tokenize/slice clauses → otherwise return `{"similar": [[query]]}` so the whole string becomes ONE similar() clause downstream. Non-string input is never SQL.

**Invariant:** The gate is SUBSTRING-based, not grammar-based — any string containing "select ... from txtai" parses as SQL even if the rest is garbage; anything else must survive the pipeline as a similarity query, never raise at dispatch time. Porters who substitute a real SQL parser for this gate break natural-language search unless they keep the non-SQL → single-similar fallback.

**Probe:** `test/python/testdatabase/testsql.py:testIsSQL` (:161-167 — `issql("select text from txtai where id = 1")` True, `issql(1234)` False); `testAggregateEmptyResults` (:38-39 — non-SQL string stays a plain query).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "txtai", query: "issql detect select from txtai natural language fallback similar", limit: 10, fields: ["signature", "name", "file"] });
```
Executed live at pin: top hit `SQL.issql :87-105` line-exact, followed by `Expression.similar :250-283`.

## Verdict
Adopt the two-part substring gate + first-statement truncation + non-SQL→single-similar fallback; adapt the magic table name `txtai` if your virtual table differs; omit multi-statement support (txtai deliberately ignores everything after the first ";"). Coverage: cited paths no_recorded_issue @ gen 2026-08-25T20:20:01Z; live pytest blocked (no torch/model downloads in lane) — deterministic probes only.
