<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :68–71 + `bulk-aggregate.ts` :89–92 — RLS group construction.

# Question
How do row-level-security conditions enter an aggregation query, and in what wrapper shape?

## Path / Symbol
`baseModel.getRlsConditions()` → wrapped as `[new Filter({ children: rlsConditions, is_group: true })]`.

## Signature
```ts
const rlsConditions = await baseModel.getRlsConditions();
const rlsFilterGroup = rlsConditions.length ? [new Filter({ children: rlsConditions, is_group: true })] : [];
```

## Data Shape
Zero conditions ⇒ empty array spliced into the conditionV2 input (no WHERE fragment); non-zero ⇒ ONE ANDed group containing ALL RLS predicates — never individual top-level filters.

## Decisive source
aggregate.ts:68–71 / bulk-aggregate.ts:89–92 — identical construction, always the FIRST element of the filter-group array. Grouping matters because getRlsConditions returns a LIST (one per applicable policy); flattening them into separate top-level AND groups would be semantically equal here but breaks the moment any policy needs internal OR — the is_group envelope preserves policy-internal structure exactly as conditionV2's tree walker expects.
Cross-reference: this is the same getRlsConditions clone-per-read seam mined in pass 10's rls capsules (rls-tree-vs-list-fail-open doctrine) — the aggregation plane consumes it identically to list/group-by planes, which is the parity guarantee that aggregations can't leak rows a list wouldn't show.

## Flow / Invariant
Porter rule: security filters go in FIRST and as ONE OPAQUE GROUP. Any later group is conjunctive with it; nothing downstream can unwrap or reorder it. If your port computes policies as raw SQL strings, wrap them so they cannot be merged into user-filter groups by future refactors.

## Probe (direct test)
From repo root:
```
grep -c 'rlsFilterGroup' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts   # => 2 (:69 decl, :76 spread)
grep -c 'getRlsConditions' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts  # => 1
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"getRlsConditions rlsFilterGroup","limit":2,"detail":"compact"}'
```
→ resolves both construction sites line-exact.

## Verdict
**Adopt.** First-position opaque-group RLS entry is the security-critical half of the filter stack; pair with aggregate-filter-stack-order.
