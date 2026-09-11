<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/single-query-cache.ts` (30L) — CE stub carrying the cache-architecture lesson.

# Question
Why is the compiled-single-query plan cache a single Redis HASH per (model, view) rather than a SET of plan keys?

## Path / Symbol
`singleQueryCacheKey(modelId, viewIdOrDefault)`; `SINGLE_QUERY_DEFAULT_VIEW = 'nc_default_view'`.

## Signature
```ts
export function singleQueryCacheKey(modelId: string, viewIdOrDefault: string): string {
  return `${CacheScope.SINGLE_QUERY}:${modelId}:${viewIdOrDefault}`;
}
```

## Data Shape
One Redis HASH per (model, view); each plan variant (`read:{flags}…`, `queries…`, `count…`, optional `:rls:*` / `:dvc:*` suffixes) is a FIELD of that hash.

## Decisive source
single-query-cache.ts:15–24 — the doc block IS the capsule: "Invalidation is therefore a single atomic DEL of this key (View.clearSingleQueryCache), which cannot leave a variant stranded: there is no separate index whose independent expiry/deletion could orphan the entries (**the cause of the Postgres 42703 'column does not exist' incident on the previous SET-indexed design**)."
:8–13 — the default-view sentinel: namespaced `nc_` so it can never collide with a real view id; exists so CE consumers import helpers under one path while EE owns the read/write bodies.
This file is also the third instance of NocoDB's same-path CE-stub doctrine (constants stay in CE, implementations in EE).

## Flow / Invariant
Design invariant for any multi-variant cached artifact: **group variants under ONE key so invalidation is one atomic op**. A companion index (SET of variant names) drifts from its members when expiry timers differ — members outliving the index become unreachable garbage; index outliving members yields stale hits that compile SQL against dropped columns (the 42703 failure mode). Hash-fields inherit the parent key's TTL, so all variants age together.

## Probe (direct test)
From repo root:
```
grep -n '42703' packages/nocodb/src/dbQueryClient/cross-db-utils/single-query-cache.ts   # => 1 (:22)
grep -c 'nc_default_view' packages/nocodb/src/dbQueryClient/cross-db-utils/single-query-cache.ts  # => 1 (:13)
grep -c 'FIELD of this hash' packages/nocodb/src/dbQueryClient/cross-db-utils/single-query-cache.ts  # => 1 (:19)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"singleQueryCacheKey SINGLE_QUERY_DEFAULT_VIEW","limit":2,"detail":"compact"}'
```
→ `...cross-db-utils.single-query-cache.singleQueryCacheKey Function ... 25-30`.

## Verdict
**Adopt.** The hash-not-set grouping rule generalizes to any plan/variant cache with compound invalidation.
