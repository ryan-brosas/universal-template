<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :404–410 (DateRange ::date casts) + `sqlite.handler.ts` :438–443 (JULIANDAY) — timestamp-vs-date range semantics.

# Question
Why does DateRange cast to DATE before differencing on pg, and what unit contract does that impose?

## Path / Symbol
DateAggregations.DateRange per dialect.

## Signature
```sql
-- pg:     MAX((x)::date) - MIN((x)::date)
-- mysql:  TIMESTAMPDIFF(DAY, MIN(x), MAX(x))
-- sqlite: CAST(JULIANDAY(MAX(x)) - JULIANDAY(MIN(x)) AS INTEGER)
```

## Data Shape
pg truncates each bound to calendar DATE (dropping time-of-day) BEFORE subtraction; mysql/sqlite difference full timestamps then floor to whole DAY units via TIMESTAMPDIFF/JULIANDAY.

## Decisive source
pg.handler.ts:404–410 — the inline comment: "The Date, DateTime, CreatedTime, LastModifiedTime columns are casted to DATE." Casting first makes 2024-01-01T23:00 → 2024-01-02T01:00 a range of **1** (calendar days), while TIMESTAMPDIFF(DAY,...) on the raw timestamps yields 0 (2 hours elapsed). The two families therefore disagree by one day on intra-day spans — and upstream ACCEPTS that because the UI labels both "days". JULIANDAY sits with mysql's family: fractional-day float minus-floored by CAST INTEGER.
The COALESCE-exemption wrap (generic.ts:109–115) does NOT exempt DateRange — empty sets coalesce to 0 days, matching "no range" rendering.

## Flow / Invariant
Porter decision: pick ONE semantic — calendar-day diff (cast-first, pg style) or elapsed-day-floor (diff-first, mysql/sqlite style) — PER ENGINE but keep the API unit integer-days either way. Cross-porting pg SQL to MySQL without dropping the cast flips boundary cases; porting TIMESTAMPDIFF to Postgres without date-truncation does the same in reverse.

## Probe (direct test)
From repo root:
```
grep -n '::date' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts        # => 4 lines (DateRange :406–407 + MonthRange :418–419)
grep -c 'TIMESTAMPDIFF' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts   # => 1 (:412)
grep -c 'JULIANDAY' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts      # => 1 line (:440 — both JULIANDAY tokens on one line; grep -c counts LINES)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"DateRange MAX MIN date","limit":3,"detail":"compact"}'
```
→ resolves all three DateRange arms line-exact.

## Verdict
**Adapt.** Port per-engine with the unit contract pinned; never translate the SQL text across engines.
