<!-- capsule-v2 -->
# partialMatchKey prefix semantics — what makes ['posts', {page: 2}] match invalidateFilters(['posts'])?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How does non-exact key matching implement "prefix" semantics over arrays AND objects consistently?

## recursive subset walk
**Path/Symbol:** `packages/query-core/src/utils.ts:partialMatchKey` (lines 248–278).
**Signature:** `partialMatchKey(a: QueryKey, b: QueryKey): boolean` — a = candidate key, b = filter key.
**Data Shape:** arbitrary nested arrays/objects/primitives; returns boolean.

### Decisive source
```ts
if (a === b) return true
if (typeof a !== typeof b) return false
if (a && b && typeof a === 'object' && typeof b === 'object') {
  if (Array.isArray(a) && Array.isArray(b)) {
    for (let i = 0; i < b.length; i++) {
      if (!partialMatchKey(a[i], b[i])) return false
    }
    return true
  }
  const bKeys = Object.keys(b)
  for (const key of bKeys) {
    if (!partialMatchKey(a[key], b[key])) return false
  }
  return true
}
return false
```

**Flow:** every comparison walks the FILTER side (b): arrays iterate only b's indices (`a` may be longer — that's the prefix property); objects iterate only b's keys (subset matching, extra members of `a` ignored). Mixed array/object or primitive mismatch → false; identical references → true short-circuit.
**Invariant:** (1) the filter is ALWAYS the driver — swapping argument order changes semantics (it would demand candidate ⊇ filter instead); (2) array-prefix + object-subset compose recursively so `['posts',{page:2}]` matches filter `['posts']` and `{page:2}` matches `{}`; (3) missing candidate slots are `undefined` and fail only against defined filter values; (4) matchQuery chooses this for non-exact filters but hash-equality (via hashQueryKeyByOptions) for exact ones.
**Probe:** `grep -n "partialMatchKey" packages/query-core/src/utils.ts` (:6 import in queryClient.ts too — `grep -c partialMatchKey packages/query-core/src/queryClient.ts` ≥ 1 via getQueryDefaults/setQueriesData consumers).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^matchQuery$", limit: 3 });
```

## Verdict
Adopt the walk verbatim for hierarchical invalidation selectors. Adapt nothing — it is 20 dependency-free lines. Omit the exact-branch interplay if your store has no custom hash fns. Direct tests: `__tests__/utils.test.tsx` (78 its) covers key matching; not executed this window.
