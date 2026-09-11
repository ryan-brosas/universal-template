<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :140–149 + `bulk-aggregate.ts` :168–170 — result-key remapping.

# Question
Why are aggregate selectors aliased by column ID and only later remapped to titles?

## Path / Symbol
Single-mode: `alias: col.id` (:115) + `idToTitle` Map applied to the result object (:140–147). Bulk-mode: bucket `f.alias` keys the row selector; inner expressions keyed by col.id.

## Signature
```ts
const idToTitle = new Map(aggregateColumns.map(({col}) => [col.id, col.title]));
for (const [key, value] of Object.entries(aggregated))
  result[idToTitle.get(key) ?? key] = value;   // ?? key keeps unknown ids visible
```

## Data Shape
Wire-out: `{ [columnTitle]: number|string }` per filter-set; SQL-level: quoted identifier aliases (knex `AS ??`) so any id/title is safe without escaping review.

## Decisive source
aggregate.ts:115 — aliasing by col.id because titles are NOT SQL-safe historically (spaces, unicode) while ids are opaque tokens knex binds as identifiers; titles also MUTATE on column rename, and a title-keyed SQL alias would break cached plans mid-flight.
:146 — `idToTitle.get(key) ?? key`: unmapped keys PASS THROUGH rather than being dropped — defensive against driver case-folding of aliases (pg lowercases unquoted identifiers) leaking through as mangled ids instead of silently vanishing from stats.
Bulk path keeps BOTH key layers: expressions dict keyed col.id inside the JSON packer, bucket alias outside (`expressions[col.id] = aggSql`, :165 vs selector alias f.alias, :169) — so one query returns {bucketAlias: {colId: value}} and the SERVICE layer owns any further translation.

## Flow / Invariant
Porter rule: SQL identifiers = stable internal tokens (ids); API keys = human-facing labels (titles). Never let user-mutable strings reach AS clauses; never drop unknown result keys during remap — log-or-passthrough preserves diagnosability when drivers fold case or columns changed between resolve and exec.

## Probe (direct test)
From repo root:
```
grep -c 'idToTitle' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts   # => 2 (map build :140 + remap :146)
grep -n '?? key' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts      # => 1 (:146)
grep -n 'expressions\[col.id\]' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts      # => 1 (:165)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"idToTitle","limit":2,"detail":"compact"}'
```
→ resolves the remap block line-exact on the twin.

## Verdict
**Adopt.** The two-key discipline (SQL=id, API=title) with passthrough-on-unknown is directly portable to any dynamic-column analytics endpoint.
