<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :59–276 vs `mysql.handler.ts` :76–274 — the Percent-family denominator shapes.

# Question
How do percent aggregations avoid division-by-zero and why does the denominator use COUNT(*) rather than the filled-count?

## Path / Symbol
PercentEmpty/PercentFilled/PercentUnique/PercentChecked/PercentUnchecked across handlers.

## Signature
```sql
-- pg/mysql:   ( <numerator> * 100.0 / NULLIF(COUNT(*), 0) )
-- sqlite:     ( <numerator> * 100.0 / IFNULL(COUNT(*), 0) )
```

## Data Shape
Numerator = the same FILTER/CASE count used by the non-percent twin; denominator = TOTAL filtered rows (COUNT(*)), not the complement count.

## Decisive source
pg.handler.ts:179–183 (PercentEmpty) — `(COUNT(*) FILTER (WHERE empty-pred) * 100.0 / NULLIF(COUNT(*), 0))`: NULLIF guards the zero-row set, returning NULL which wrap()'s COALESCE converts to **0** — so an empty view reports "0% empty" rather than NaN or an error. The `* 100.0` float literal BEFORE division forces decimal math; integer-first division would truncate every percent to 0 on engines with integer precedence.
Denominator semantics: COUNT(*) counts ALL rows in the filtered set including rows where the column is NULL — percentages are per-ROW not per-CELL-filled. A porter substituting COUNT(column) changes every percentage's meaning on sparse columns.
sqlite swaps NULLIF→IFNULL around COUNT (same guard, inverted argument order); mysql keeps NULLIF like pg.

## Flow / Invariant
Porter checklist: float-literal multiplication before division; total-row denominator; null-guard matching your engine's COALESCE family; result flows through the shared COALESCE-to-0 wrap. All four together reproduce NocoDB's percent contract exactly.

## Probe (direct test)
From repo root:
```
grep -c '100.0' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | head -1   # => 9 percent sites (6 common + 2 boolean + ... see grep -n)
grep -n 'NULLIF(COUNT' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | wc -l  # => 9
grep -n 'IFNULL(COUNT' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts | wc -l  # => 9
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"NULLIF IFNULL percent 100.0","limit":4,"detail":"compact"}'
```
→ resolves the percent families across all three handlers.

## Verdict
**Adopt.** The four-part percent recipe is identical across families once you see it — port as one pattern.
