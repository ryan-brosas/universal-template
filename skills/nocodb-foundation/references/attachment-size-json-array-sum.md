<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :430–445 + mysql.handler.ts :430–445 + sqlite.handler.ts :457–474 (attachment family) + boolean quartet pg :355–389 / mysql :362–397 / sqlite :390–424.

# Question
How is attachment size summed over a JSON array column, and how do boolean counts stay engine-true?

## Path / Symbol
`AttachmentAggregations.AttachmentSize`; `BooleanAggregations.{Checked,Unchecked,PercentChecked,PercentUnchecked}`.

## Signature
```ts
// pg:        SUM((SELECT COALESCE(SUM((json_object ->> 'size')::int), 0) FROM jsonb_array_elements(??::jsonb) AS json_array(json_object)))
// mysql:     (SELECT SUM(JSON_EXTRACT(json_object,'$.size')) FROM ?? CROSS JOIN JSON_TABLE(CAST(?? AS JSON),'$[*]' COLUMNS (json_object JSON PATH '$')) AS json_array)
// sqlite:    (SELECT SUM(CAST(json_extract(value,'$.size') AS INTEGER)) FROM ??, json_each(??))
```

## Data Shape
All three are SELF-CONTAINED scalar subqueries (their own FROM) — on mysql/sqlite bound to `[subAggFrom, subAggCol]` from the filtered derived table; on pg bound to the inline column_query with a `::jsonb` cast.

## Decisive source
pg.handler.ts:437–440 — pg is the ONLY dialect binding the raw column expression (`??::jsonb`) instead of the derived table; the inner SELECT+COALESCE(...,0) makes empty arrays sum to 0 rather than NULL so the shared COALESCE wrap is belt-and-suspenders here.
mysql.handler.ts:437–439 — JSON_TABLE LATERAL join over `CAST(col AS JSON)` — required because MySQL has no implicit array-lateral; the COLUMNS clause names each element json_object.
sqlite.handler.ts:463–466 — json_each table-valued function; CAST to INTEGER because sqlite's json_extract returns REAL for large sizes.
Boolean trio asymmetry: pg tests `= true / = false OR = NULL` (:362–370); mysql uses literals `= true/= false OR IS NULL` (:369–378); sqlite uses `= 1 / = 0 OR IS NULL` (:397–405) — storage-class truth per engine. NOTE the pg Unchecked predicate `(??) = NULL` is SQL-null comparison (always unknown ⇒ row not counted by FILTER... but FILTER treats unknown as false, so unchecked-count relies on the `= false` arm plus rows where driver returns literal false; porters must reproduce ENGINE BEHAVIOR not textbook three-valued logic here).

## Flow / Invariant
Invariant: attachment-size must be computed over FILTERED sets (hence subAggFrom/subAggCol on mysql/sqlite) and must never NULL on empty arrays. Boolean percent formulas reuse the same `* 100.0 / NULLIF|IFNULL(COUNT(*), 0)` denominator shape as the common family — zero-row sets yield NULL→coalesced 0, never a division error.

## Probe (direct test)
From repo root:
```
grep -n 'jsonb_array_elements' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts    # => 1 (:438)
grep -n 'JSON_TABLE' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts          # => 1 (:438)
grep -n 'json_each' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts          # => 1 (:465)
grep -c '= true' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts                # => 2 (Checked :362 + PercentChecked :374 — one line each, grep -c counts lines)
grep -c '= 1 THEN' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts          # => 2 (Checked :397 + PercentChecked :409)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"AttachmentSize jsonb_array_elements JSON_TABLE json_each","limit":4,"detail":"compact"}'
```
→ resolves all three handlers' attachment methods.

## Verdict
**Adapt.** Three engine-native array-unwinds, one contract: filtered input, integer byte total, zero-safe denominators.
