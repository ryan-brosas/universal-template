<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :59–273 (common) vs `mysql.handler.ts` :76–274 / `sqlite.handler.ts` :76–272.

# Question
How do identical count/percent semantics get expressed as FILTER on pg and CASE WHEN elsewhere — without semantic drift?

## Path / Symbol
CommonAggregations.{Count, CountEmpty, CountFilled, CountUnique, PercentEmpty, PercentFilled, PercentUnique, None} × 3 dialect handlers.

## Signature
```sql
-- pg   (FILTER):     COUNT(*) FILTER (WHERE (x) IS NULL OR (x) = '')
-- mysql/sqlite (CASE): SUM(CASE WHEN (x) IS NULL OR (x) = '' THEN 1 ELSE 0 END)
```

## Data Shape
Percent forms wrap the same predicate in `( ... * 100.0 / NULLIF(COUNT(*),0) )` (pg/mysql) or `/ IFNULL(COUNT(*),0)` (sqlite) — NULLIF vs IFNULL is the dialect's null-denominator guard.

## Decisive source
The three-way column-type split repeated in every family: (1) JSON columns get special treatment because DISTINCT can't order jsonb — pg casts to text inside COUNT(DISTINCT ((x)::text)) (:126–131), mysql uses JSON_UNQUOTE(JSON_EXTRACT(x,'$')) (:136–141), sqlite json_extract(x,'$') (:135–140); empty-test differs too: pg IS NULL, mysql JSON_LENGTH IS NULL, sqlite json_array_length IS NULL. (2) The typed-column list (dates/numerics/system) drops the `!= ''` arm entirely (IS NOT NULL only). (3) String-ish columns keep the two-arm predicate with the dialect sentinel.
CountUnique's typed branch binds the SAME expression twice (`COUNT(DISTINCT CASE WHEN (x) IS NOT NULL THEN (x) END)`) — the CASE both filters and projects.
None ⇒ undefined from the switch (no case) ⇒ selector skipped upstream.

## Flow / Invariant
Semantic parity table a porter must carry over whole: FILTER↔SUM(CASE) is mechanical (pg ships 24 `FILTER (WHERE)` clauses total across its families); NULLIF↔IFNULL is mechanical; but the JSON-family predicates are ENGINE-SPECIFIC (jsonb vs JSON_LENGTH vs json_array_length) and must never be cross-copied. Percent denominators are COUNT(*) of the FILTERED set — soft-delete/RLS already applied at orchestration level, so the SQL must not re-filter.

## Probe (direct test)
From repo root:
```
grep -c 'SUM(CASE WHEN' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts # => 12
grep -c 'IFNULL(COUNT' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts # => 9
grep -c 'NULLIF(COUNT' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts     # => 9
grep -rc 'JSON_LENGTH\|json_array_length' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts | awk -F: '{s+=$NF} END {print s}'   # => 4 lines (2 per file)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"CountEmpty CountFilled FILTER SUM CASE","limit":4,"detail":"compact"}'
```
→ resolves the common() methods across all three handlers.

## Verdict
**Adopt.** This is the reference translation matrix FILTER/CASE + NULLIF/IFNULL + per-engine JSON predicates for any analytics port.
