<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :66–81, `mysql.handler.ts` :86–98, `sqlite.handler.ts` :86–98 — the CountEmpty JSON special-case trio.

# Question
Why does "count empty cells in a JSON column" need a different predicate per dialect even though all three have JSON types?

## Path / Symbol
CountEmpty / PercentEmpty `[UITypes.JSON]` branches.

## Signature
```sql
-- pg:      COUNT(*) FILTER (WHERE (x) IS NULL)                          -- jsonb ''-comparison illegal AND meaningless
-- mysql:   SUM(CASE WHEN JSON_LENGTH(x) IS NULL THEN 1 ELSE 0 END)       -- NULL only when x is NULL; '[]' counts FILLED? no...
-- sqlite:  SUM(CASE WHEN json_array_length(x) IS NULL THEN 1 ELSE 0 END)
```

## Data Shape
The JSON branch replaces BOTH arms of the two-arm predicate (`IS NULL OR = sentinel`) with a single engine-specific nullness probe.

## Decisive source
pg.handler.ts:69–75 — JSON skips the condnValue arm entirely: comparing jsonb to a string literal raises "invalid input type" on PG, and the comment in buildContext (:23–25) already establishes PG enum/typed rejection of ''. So pg JSON empty == IS NULL.
mysql.handler.ts:87–93 / sqlite.handler.ts :87–93 — JSON_LENGTH/json_array_length return NULL **only for SQL NULL input** (they return non-null for '[]' and '{}'), so these probes are exactly IS NULL in disguise — chosen because direct `(x) IS NULL` on a TEXT-stored json column misses driver-wrapped values. The functional difference vs pg: mysql/sqlite never treat malformed-but-nonnull text as filled-by-content — they count it via the length probe's non-null return.
PercentEmpty twins wrap identically (:171–183 pg, :177–188 mysql, :176–188 sqlite).

## Flow / Invariant
Porter trap: JSON emptiness is NOT `= '{}'` or `JSON_LENGTH(x)=0` anywhere in this codebase — an EMPTY ARRAY is a FILLED cell by contract (it holds content). Porters who "fix" this to count empty containers as empty change every stats widget over attachment-like columns. The three predicates agree semantically (NULL-only-is-empty) while differing mechanically per storage reality.

## Probe (direct test)
From repo root:
```
sed -n '69,75p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'IS NULL'          # => 1
grep -n 'JSON_LENGTH' packages/nocodb/src/dbQueryClient/aggregations/handlers/mysql.handler.ts                    # => 2 (:89,:180)
grep -n 'json_array_length' packages/nocodb/src/dbQueryClient/aggregations/handlers/sqlite.handler.ts             # => 2 (:89,:179)
grep -rn "= '{}'\|JSON_LENGTH(.*) = 0\|json_array_length(.*) = 0" packages/nocodb/src/dbQueryClient/ | wc -l      # => 0 (empty-container-is-filled invariant holds)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"CountEmpty JSON_LENGTH json_array_length","limit":3,"detail":"compact"}'
```
→ resolves the three JSON branches line-exact.

## Verdict
**Adapt.** Keep the NULL-only emptiness contract and re-map the length probes to your engines' JSON functions.
