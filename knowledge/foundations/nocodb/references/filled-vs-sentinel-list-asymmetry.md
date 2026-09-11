<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :82–123 + `mysql.handler.ts` :99–134 — the CountFilled typed-column lists.

# Question
Why does CountFilled's "typed" list include MORE column types than its CountEmpty sentinel list, and what does each list actually gate?

## Path / Symbol
The UITypes arrays inside `common()`'s CountFilled / PercentFilled / CountUnique / PercentUnique branches (per handler).

## Signature
```ts
// filled-typed arm:   COUNT(*) FILTER (WHERE (x) IS NOT NULL)                      -- no sentinel comparison at all
// filled-string arm:  COUNT(*) FILTER (WHERE (x) IS NOT NULL AND (x) != '')
```

## Data Shape
pg CountFilled typed list (:86–106): CreatedTime…UUID **plus JSON, LinkToAnotherRecord, Lookup** — 19 entries vs the buildContext sentinel's 16. mysql twin (:100–119): same minus AutoNumber/UUID ⇒ 17.

## Decisive source
The comment at pg.handler.ts:83–84 states the design: "The condition IS NOT NULL AND (column_query) != 'NULL' is not same for the following column_query types: Hence we need to handle them separately." For FILLED-counting, typed columns only need the IS NOT NULL arm because comparing them to a string sentinel is meaningless-or-fatal; string-ish columns need the second arm so a literal empty-string cell counts as EMPTY. The wider list here vs buildContext is not drift: buildContext's sentinel feeds BOTH arms of empty-tests and numeric comparators (`!= condnValue` in Avg), while the filled-test only needs to know whether a ''-comparison is SAFE. JSON/Lookup/LTAR join the typed side here because their values never stringify to ''.
PercentFilled/CountUnique/PercentUnique repeat identical lists per family (pg :135–165/:187–218/:235–265) — four copies per handler, kept inline deliberately.

## Flow / Invariant
Porter rule: two distinct lists per dialect with different membership rules — SENTINEL LIST = "columns where ''-comparison breaks" (drives condnValue choice); TYPED-FILLED LIST = "columns where ''-comparison is pointless" (drives one-arm predicate). Merging them over-applies sentinels to rating-like columns or under-applies them to native enums. The duplication across four count families is upstream's trade for per-family readability; preserve it rather than refactoring into shared predicates when porting faithfully.

## Probe (direct test)
From repo root:
```
awk 'NR>=85 && NR<=107' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'UITypes\.'    # => 19 (pg CountFilled typed list)
awk 'NR>=100 && NR<=119' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts | grep -c 'UITypes\.' # => 17 (mysql twin)
grep -c 'handle them separately' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts          # => 4 (Filled/Unique/PercentFilled/PercentUnique)
grep -n 'LinkToAnotherRecord' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts             # => first hit :104 (filled list)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"CountFilled typed column list","limit":3,"detail":"compact"}'
```
→ resolves both common() methods line-exact.

## Verdict
**Adapt.** Port both lists with their distinct semantics documented; do NOT unify them.
