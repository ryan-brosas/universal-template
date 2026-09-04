<!-- capsule-v2 -->
# Rejection-Evicting Source Cache — when must a promise cache DELETE failed entries instead of retaining them like the main fetch cache does?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** The registry fetch cache deliberately keeps rejected promises until an explicit clear (see `fetch-promise-cache`), yet the GitHub source cache evicts them — what distinguishes the two, and what does a correct eviction look like?

## promise-before-await + identity-guarded catch eviction
**Path/Symbol:** `packages/shadcn/src/registry/github.ts:readWithCache` (:170-189); same pattern in `packages/shadcn/src/registry/github-ref.ts:resolveGitHubRef` (:46-51). **Contrast:** `fetcher.ts` registry cache (pass-1 capsule `fetch-promise-cache`) retains rejections until `clearRegistryCache()`.
**Signature:** `readWithCache(key: string, fetcher: () => Promise<string>): Promise<string>` over a per-invocation `sourceCache: Map<string, Promise<string>>`.
**Data Shape:** Cache maps `${mode}:${owner}/${repo}/${sha}/${filePath}` or `anonymous:<url>` (and `owner/repo#ref` for refs) to the IN-FLIGHT promise; the Map instance is created once per command and threaded through concurrent item fetches and recursive dependency resolution — it doubles as the WeakMap anchor for auth state.

### Decisive source
```ts
const readWithCache = (key: string, fetcher: () => Promise<string>) => {
  if (options.useCache !== false && sourceCache.has(key)) {
    return sourceCache.get(key)!            // concurrent callers share one flight
  }
  const promise = fetcher()
  if (options.useCache !== false) {
    sourceCache.set(key, promise)           // cached BEFORE awaiting
    // Evict rejections so a transient failure is not replayed for the rest
    // of the invocation.
    promise.catch(() => {
      if (sourceCache.get(key) === promise) {   // identity guard
        sourceCache.delete(key)
      }
    })
  }
  return promise
}
```

**Flow:** first caller stores the pending promise synchronously so parallel readers dedupe onto one flight → when that promise rejects, the attached handler deletes the entry ONLY if the map still holds this exact promise (a later successful overwrite is never clobbered) → the next reader re-fetches fresh. The eviction is deliberate because these are per-invocation source reads of re-readable files: one transient 500 during tree resolution must not poison every subsequent dependency read, unlike the process-lifetime registry fetch cache whose poison retention is bounded by explicit clearing.
**Invariant:** Store-before-await is non-negotiable (otherwise two callers race into two flights). Eviction must be identity-guarded and must never swallow the rejection itself (the original caller still receives it). `useCache === false` bypasses both read AND write.
**Probe:** `packages/shadcn/src/registry/github.test.ts` :1149-1184 — root returns 500 through a caller-supplied `sourceCache`, handlers then flip to success, SAME Map yields a good item on retry. `packages/shadcn/src/registry/github-ref.test.ts` :112-130 — failed ref resolution evicted, second call re-runs git. Runner caveat: node_modules absent in checkout — pinned by direct reads.
**Coverage:** github.ts + github-ref.ts `no_recorded_issue` @ generation 2026-08-25T20:00:37Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "readWithCache sourceCache evict rejected promise transient failure retry", limit: 8 });
// observed: readWithCache #1 (github.ts:170-189)
```

## Verdict
Adopt store-before-await plus identity-guarded rejection eviction for short-lived, re-readable resource caches; keep retain-until-clear only for long-lived caches where you want failures visible until explicitly reset. Adapt the key grammar to your transport modes. Omit nothing structural — the contrast with `fetch-promise-cache` IS the design lesson: cache lifetime policy decides eviction policy.
