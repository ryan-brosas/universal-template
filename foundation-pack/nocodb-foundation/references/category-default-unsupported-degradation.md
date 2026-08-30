<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts` :66–86 — default-undefined category methods.

# Question
What happens when a dialect handler doesn't override a category — and why is that silent at the SQL layer?

## Path / Symbol
`GenericAggregationHandler.{common, numerical, boolean, date, attachment}` base bodies: `return undefined;`.

## Data Shape
Five category methods, all defaulting to undefined; concrete handlers override 4–5 of them (pg/mysql/sqlite all five; CE stubs zero).

## Decisive source
generic.ts:66–67 — the comment states the contract: "Category strategies — default to 'unsupported' (undefined). Dialect handlers override the ones they implement." Combined with generate()'s `if (!aggregationSql) return undefined` (:52–54), an unimplemented category yields NO selector rather than broken SQL.
Downstream consequence chain (cross-db-utils): applyAggregation receives undefined → skips pushing a selector → aggregate() checks `if (!selectors.length) return {}` (aggregate.ts:122–124) — so requesting `attachmentSize` on a dialect lacking the attachment category returns an EMPTY STATS OBJECT for that column while other columns still aggregate. Per-column degradation, never per-request failure.
The contrast with validateAggregationColType's notImplemented throw (applyAggregation.ts:69–74) completes the matrix: TYPE×AGG invalid = loud 501; DIALECT lacks category = silent omission. Both are "unsupported" from the user's view but only one is actionable by them.

## Flow / Invariant
Porter rule: choose the silence/throw channel by WHO can fix it — user picked an unsupported combo ⇒ throw with the catalog message; platform hasn't implemented a category for this engine ⇒ omit silently and let other columns succeed. Flipping these either spams 501s across mixed-dialect dashboards or hides real gaps behind empty widgets forever.

## Probe (direct test)
From repo root:
```
sed -n '66,87p' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts | grep -c 'return undefined'   # => 5
grep -n 'default to .unsupported.' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts             # => 1 (:66)
sed -n '52,54p' packages/nocodb/src/dbQueryClient/aggregations/handlers/generic.ts | grep -c 'return undefined'   # => 1 (generate guard)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"category strategies default unsupported","limit":2,"detail":"compact"}'
```
→ resolves the five default methods line-exact.

## Verdict
**Adopt.** The two-channel unsupportability doctrine (user-actionable throws, platform-gaps degrade) generalizes beyond aggregation.
