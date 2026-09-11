<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :17–57 vs `mysql.handler.ts` :46–71 / `sqlite.handler.ts` :46–71 — the sentinel-list DIFF.

# Question
Which columns get the NULL sentinel on pg but NOT on mysql/sqlite, and why does the list length differ by one?

## Path / Symbol
The `UITypes.[...]` array inside each handler's buildContext (the "typed columns" list) + pg's extra UUID entry + pg_enum escape.

## Signature
Same shape all three: `if ([...UITypes].includes(column.uidt) || [DATE, NUMERIC].includes(parsedFormulaType)) condnValue = 'NULL'`.

## Data Shape
pg list (:29–45): CreatedTime, LastModifiedTime, Date, DateTime, Number, Decimal, Year, Currency, Duration, Time, Percent, Rollup, Links, ID, AutoNumber, **UUID** — 16 entries.
mysql/sqlite lists (:48–63 both): identical MINUS AutoNumber and UUID — 14 entries.

## Decisive source
pg.handler.ts:26 — the pg-only branch `isNativePgEnum = !!column.internal_meta?.pg_enum_type_name` exists because Postgres has NATIVE enum types that reject `''`; MySQL/SQLite store enums as strings where `= ''` is a valid comparison. That same native-typing gap explains the list diff: on PG, UUID/AutoNumber are real typed columns whose comparison to '' is a cast ERROR, so they must ride the NULL sentinel; on mysql/sqlite they're stored as VARCHAR where '' comparison is merely meaningless-but-safe, and upstream chose the shorter list.
Cross-check in-file: pg's CountFilled/CountUnique/PercentFilled/PercentUnique typed lists (:87–104 etc.) DO include AutoNumber+UUID+JSON+Lookup — the SENTINEL list is deliberately narrower than the FILLED-test list because the filled test only needs IS NOT NULL (no '' comparison), while the sentinel arms compare against condnValue.
Formula DATE/NUMERIC types join the NULL arm identically in all three handlers (:46–49 / :64–66 / :64–66).

## Flow / Invariant
Porter rule: sentinel selection is a function of STORAGE TYPE, not UI type alone. When porting, re-derive which UITypes map to natively-typed storage on YOUR engine; copying either list verbatim misclassifies empty cells on at least one engine. The narrower-vs-wider list asymmetry between sentinel and filled predicates is intentional, not drift.

## Probe (direct test)
From repo root:
```
sed -n '28,50p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'UITypes\.'        # => 16
awk 'NR>=48 && NR<=63' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts | grep -c 'UITypes\.'    # => 14
awk 'NR>=46 && NR<=72' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts | grep -c 'UUID'   # => 0 in sentinel region
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"buildContext condnValue sentinel UITypes","limit":4,"detail":"compact"}'
```
→ resolves all three buildContext methods line-exact for side-by-side diffing.

## Verdict
**Adapt.** Port the MECHANISM (native-type ⇒ NULL sentinel); re-derive the lists per target engine.
