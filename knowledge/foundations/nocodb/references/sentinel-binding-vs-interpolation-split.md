<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :285–295 (Avg Rating) + `mysql.handler.ts` :284–293 — the Avg sentinel-comparison asymmetry.

# Question
Why does pg's Rating-Avg use FILTER while mysql's uses CASE — and why does the comparison direction differ from CountEmpty's?

## Path / Symbol
Rating branches in `numerical()` across handlers; contrast with `condnValue` usage in common().

## Signature
```sql
-- pg Rating Avg:    AVG((x)) FILTER (WHERE (x) != 0)          -- binds condnValue as a PARAMETER (??)
-- mysql Rating Avg: AVG(CASE WHEN (x) != 0 THEN (x) ELSE NULL END)  -- interpolates ${condnValue} as TEXT
```

## Data Shape
pg passes condnValue through knex bindings (`[column_query, column_query, condnValue]`) so the literal 0 arrives typed; mysql/sqlite interpolate `${condnValue}` directly into the CASE text.

## Decisive source
pg.handler.ts:286–292 — Rating Avg/Min/Stddev each bind `condnValue` as a positional parameter (three-element binding arrays); the same handler's common() family INTERPOLATES `${condnValue}` into SQL text (:77, :120, :167). Same file, two styles: the numerical() predicates compare against a VALUE (0 or NULL) where binding is safe and keeps types honest, while common()'s empty-tests embed a compile-time constant chosen per column class. mysql.handler.ts mirrors both styles identically (:287 CASE-interpolated vs :95 SUM-CASE interpolated).
The functional reason FILTER can't appear on mysql is engine absence of the clause; the reason BINDING appears only on pg's numerical arms is that FILTER's parameter position accepts bindings cleanly whereas the composed CASE strings are already template-built.

## Flow / Invariant
Porter trap: condnValue participates BOTH as bound parameter and interpolated literal depending on family+dialect — porters who unify to one style hit either driver type-inference errors (binding NULL into IS NOT NULL comparators) or injection-shaped text bugs when values stop being constants. The invariant: interpolation is ONLY ever used with compile-time constant sentinels (''/NULL/0), never runtime data.

## Probe (direct test)
From repo root:
```
sed -n '286,292p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'condnValue'   # => 1 binding usage
sed -n '76,79p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'condnValue}'   # => 1 interpolation
grep -c 'FILTER (WHERE (??) != ??)' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts        # => 4 (Avg/Min/Stddev rating arms :287/:301/:317 + the Rating-Max composite raw string :331; the :326–329 comment above it reads 'FILTER (WHERE ... != 0)' with literal dots so it never matches — annotate each site from live `grep -n` output, never from neighboring code)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"Avg Rating FILTER condnValue","limit":3,"detail":"compact"}'
```
→ resolves the rating arms line-exact.

## Verdict
**Adapt.** Keep the two binding styles where they are; document which one your port's driver tolerates per clause type.
