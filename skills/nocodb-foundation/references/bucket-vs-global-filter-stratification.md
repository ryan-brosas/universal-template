<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts` :119–145 — the six-group filter stack (bulk variant).

# Question
How does a bucket's own `where` differ from the request-level `where`, and why is extractFilterFromXwhere called twice per bucket?

## Path / Symbol
Inner conditionV2 array in bulkAggregate — groups: RLS, view-root, args.filterArr, TOP-LEVEL where (re-extracted inline), BUCKET aggFilter (f.where), parsedFilterArrJson.

## Signature
```ts
new Filter({ children: extractFilterFromXwhere(baseModel.context, where, aliasColObjMap).filters, ... }),   // top-level
new Filter({ children: aggFilter, ... })   // bucket-level: from f.where extracted in the loop preamble (:98-102)
```

## Data Shape
Two distinct `where` strings: ctx.args.where (request-wide, same for every bucket) and f.where (per-bucket). Both parse through the SAME extractFilterFromXwhere against the shared aliasColObjMap.

## Decisive source
bulk-aggregate.ts:98–102 — bucket's aggFilter extracted ONCE per bucket into the loop preamble; :119–129 — the top-level where is re-extracted INLINE inside the group array on every iteration. The duplication is real but harmless-by-design: extraction is pure (no DB), and hoisting it would save only M−1 parses of a string usually shorter than the filterArr. The ORDER matters more: top-level where binds as an ANDed group BEFORE the bucket's own so a bucket can never widen what the view/request already restricted.
parsedFilterArrJson rides LAST (:138–145) — the validated JSON filters apply after everything, mirroring how the single path orders filterArr before xwhere.

## Flow / Invariant
Porter rule: per-bucket scoping must be ADDITIVE to global scoping, and group order = authority order (RLS first, bucket-local last-but-one, validated JSON last). A porter who merges args.where INTO each bucket's f.where loses the ability to express "same widget grid, different slice" and double-counts the global predicate.

## Probe (direct test)
From repo root:
```
grep -n 'extractFilterFromXwhere' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts   # => 3 sites (:98,:125,:11-import)
sed -n '107,148p' packages/nocodb/src/dbQueryClient/cross-db-utils/bulk-aggregate.ts | grep -c 'logical_op'   # => 3 explicit AND groups in-window (RLS + view-root ride the spread/conditional without logical_op)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"aggFilter bulkFilterList conditionV2","limit":2,"detail":"compact"}'
```
→ resolves the bucket loop region line-exact.

## Verdict
**Adopt.** Global-vs-bucket filter stratification with additive AND semantics ports directly to any multi-slice stats API.
