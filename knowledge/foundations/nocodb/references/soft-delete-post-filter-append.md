<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts` :102–105 + `bulk-aggregate.ts` :150–153 — soft-delete placement.

# Question
Why is the soft-delete filter appended OUTSIDE the conditionV2 group array?

## Path / Symbol
`const softDeleteFilter = await baseModel.getSoftDeleteFilter(); if (softDeleteFilter) qb.where(softDeleteFilter);`

## Signature
conditionV2 receives the four Filter groups; the soft-delete predicate rides a raw `qb.where(...)` AFTER that call returns.

## Data Shape
getSoftDeleteFilter returns either null (model has no soft-delete column) or a raw SQL/builder fragment — NOT a Filter tree node, which is exactly why it can't join conditionV2's input array.

## Decisive source
aggregate.ts:102–105 (single, applied to shared qb) / bulk-aggregate.ts:150–153 (per-bucket tQb inside the loop). Both sites sit AFTER conditionV2 and BEFORE selector generation, so every aggregate expression compiled against these builders sees deleted rows excluded.
Why outside: conditionV2 compiles Filter TREES with parameter binding per node; getSoftDeleteFilter emits a pre-built fragment in knex's own callback form. Mixing forms would require re-wrapping; upstream keeps the two compilation paths separate so neither parser has to understand the other. The ordering invariant does the security work regardless: appended WHEREs are always conjunctive.
Cross-ref: same pattern at BaseModelSqlv2 list/group-by planes (mined earlier passes) — aggregations copy the ESTABLISHED idiom rather than inventing a tree form.

## Flow / Invariant
Porter rule: deleted-row exclusion must be conjunctive and unconditional — appending after all user filters means no user filter combination can resurrect soft-deleted rows. If your port models soft-delete as a normal filter group INSIDE the user-editable stack, users can negate it with a NOT group.

## Probe (direct test)
From repo root:
```
grep -n 'getSoftDeleteFilter' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts   # => 1 + 1 (:102,:150)
sed -n '102,106p' packages/nocodb/src/dbQueryClient/cross-db-utils/aggregate.ts | grep -c 'qb.where'   # => 1
sed -n '150,154p' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts | grep -c 'tQb.where'   # => 1
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"getSoftDeleteFilter aggregate","limit":2,"detail":"compact"}'
```
→ resolves both append sites line-exact.

## Verdict
**Adopt.** Post-tree conjunctive append is the deletion-safety idiom; keep it outside any user-influenced filter structure.
