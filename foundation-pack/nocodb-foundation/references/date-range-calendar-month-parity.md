<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :391–428 (date) + mysql.handler.ts :399–428 + sqlite.handler.ts :426–455.

# Question
Why do the three date-aggregation recipes disagree on purpose, and which one is "wrong" if copied between dialects?

## Path / Symbol
DateAggregations.{EarliestDate, LatestDate, DateRange, MonthRange} per handler.

## Signature
```ts
// pg      DateRange:  MAX((??)::date) - MIN((??)::date)                    -- integer day count
// mysql   DateRange:  TIMESTAMPDIFF(DAY, MIN(??), MAX(??))                 -- integer day count
// sqlite  DateRange:  CAST(JULIANDAY(MAX(??)) - JULIANDAY(MIN(??)) AS INTEGER)
```

## Decisive source
pg.handler.ts:411–422 — MonthRange carries THE decisive comment: "(EXTRACT(YEAR FROM MAX)*12 + EXTRACT(MONTH FROM MAX)) - (...MIN...) — Calendar-month diff (matches SQLite / MySQL / JS reducer). AGE() would return elapsed-time-in-whole-months instead, which is off by one when the day-of-month of the max is earlier than that of the min (e.g. 2024-01-15 → 2025-01-01 is 11 months 17 days under AGE, but 12 calendar months apart)." So pg deliberately does NOT use its native age().
mysql MonthRange (:417–421): PERIOD_DIFF(DATE_FORMAT(MAX,'%Y%m'), DATE_FORMAT(MIN,'%Y%m')) — same calendar-month semantics via period arithmetic.
sqlite MonthRange (:444–447): strftime('%Y')*12+strftime('%m') subtraction — the exact formula the pg comment says all three share.
Earliest/Latest are plain MIN/MAX everywhere; these two names are ALSO the COALESCE-exempt pair in generic wrap (generic.ts:109–115) — the only aggregations allowed to return NULL on empty sets.

## Flow / Invariant
Porter traps: (1) DateRange must count DAYS as an integer on every engine — pg's date-minus-date yields an int, but copying it to MySQL yields a broken interval string; TIMESTAMPDIFF is required. (2) MonthRange is CALENDAR-month diff everywhere; using native elapsed-time functions (pg AGE) breaks parity with the SDK's JS reducer and with the other dialects. (3) The NULL-allowed pair is fixed by name in wrap() — adding a new date aggregation silently inherits COALESCE-to-0 unless the exemption list is revisited.

## Probe (direct test)
From repo root:
```
grep -c 'PERIOD_DIFF' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts   # => 1 (:419)
grep -c 'JULIANDAY' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts    # => 1 (:440)
grep -c 'EXTRACT(YEAR' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts     # => 2
grep -c 'AGE()' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts            # => 1 (:411 comment only — no SQL usage; the =0 claim in earlier drafts was wrong)
grep -n 'EarliestDate' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts        # => 1 (:110 COALESCE exemption)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"MonthRange PERIOD_DIFF JULIANDAY EXTRACT","limit":3,"detail":"compact"}'
```
→ resolves the three handlers' date methods line-exact.

## Verdict
**Adapt.** Port each recipe per-engine; never translate SQL text across dialects for date arithmetic. Preserve the calendar-month contract and the two-name COALESCE exemption.
