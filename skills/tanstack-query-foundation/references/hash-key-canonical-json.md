<!-- capsule-v2 -->
# hashKey canonical JSON — why is {a:1,b:2} the same cache entry as {b:2,a:1}?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How are structurally-equal-but-differently-ordered query keys hashed to one cache slot without a real deep-hash algorithm?

## hashKey via sorted-key replacer
**Path/Symbol:** `packages/query-core/src/utils.ts:hashKey` (lines 232–243) + `hashQueryKeyByOptions` (:220–226).
**Signature:** `hashKey(queryKey): string` — `JSON.stringify(queryKey, replacer)` where replacer sorts plain-object keys; `hashQueryKeyByOptions(queryKey, options?)` honors a custom `queryKeyHashFn`.
**Data Shape:** input: readonly unknown[] key; output: stable string used as Map key in QueryCache.

### Decisive source
```ts
export function hashKey(queryKey: QueryKey | MutationKey): string {
  return JSON.stringify(queryKey, (_, val) =>
    isPlainObject(val)
      ? Object.keys(val)
          .sort()
          .reduce((result, key) => {
            result[key] = val[key]
            return result
          }, {} as any)
      : val,
  )
}
```

**Flow:** defaultQueryOptions computes queryHash once (`options.queryHash ?? hashQueryKeyByOptions(...)`) and it becomes the cache identity; matchQuery's exact branch re-hashes the filter through the SAME function so custom hash fns compose everywhere.
**Invariant:** (1) only PLAIN objects get sorted (isPlainObject gate — class instances, Dates, Maps keep insertion-order serialization and therefore do NOT canonicalize); (2) key ORDER of object members is not identity, but array ORDER is (arrays serialize positionally); (3) undefined values vanish under JSON.stringify — `['a', undefined]` and `['a']` collide by design; (4) a custom queryKeyHashFn replaces hashing globally per-query — filters must route through hashQueryKeyByOptions or exact matching breaks.
**Probe:** self-contained live probe from repo root (registerHooks resolves extensionless relative imports): `node --experimental-strip-types -e "const{registerHooks}=require('node:module');registerHooks({resolve(s,c,next){if(s.startsWith('.')&&!/\.[a-z]+$/.test(s))s+='.ts';return next(s,c)}});import('./packages/query-core/src/utils.ts').then(m=>console.log('HASH-EQ:',m.hashKey(['a',{b:2,a:1}])===m.hashKey(['a',{a:1,b:2}])))"` → prints `HASH-EQ: true`. Executed GREEN this pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^hashQueryKeyByOptions$", limit: 3 });
```

## Verdict
Adopt sorted-key-replacer hashing for any string-keyed store keyed by structured values — 10 lines, zero deps, deterministic across runtimes with identical JSON.stringify. Adapt isPlainObject strictness if your keys carry prototypes (they will silently missort). Omit the custom-fn plumbing if you have no user-supplied hashers.
