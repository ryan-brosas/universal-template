<!-- capsule-v2 -->
# Cache save-skip + restore-keys contract — how do you avoid redundant cache writes while keeping stale-cache fallback?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** What is the full decision tree for restoring and saving the analysis cache, including the "already exists" race?

## Reserved-key equality short-circuit, error-string matching, default-branch gating
**Path/Symbol:** `scan/src/utils.ts:restoreCaches` (:430-460), `uploadCaches` (:394-421), `isNeedToUploadCache` (:465-484), `ENABLE_USE_CACHE_OPTION_WARNING` (:71-72).
**Signature:** `restoreCaches(cacheDir, primaryKey, additionalCacheKey, execute): Promise<string>` (returns the ACTUAL matched key or ''); `uploadCaches(cacheDir, primaryKey, reservedCacheKey, execute)`.
**Data Shape:** GitHub cache semantics — exact primary match or any key sharing a restore-key prefix; saves are immutable per key.

### Decisive source
```ts
// uploadCaches:
if (primaryKey === reservedCacheKey) {
  core.info(`Cache with key ${primaryKey} already exists, skipping cache uploading...`)
  return
}
try {
  await cache.saveCache([cacheDir], primaryKey)
} catch (error) {
  const errorMessage = (error as Error).message
  if (errorMessage.includes('Cache already exists.')) {   // concurrent-run race
    core.info(`Cache with key ${primaryKey} already exists, skipping cache uploading...`)
  } else {
    core.warning(`Failed to upload caches – ${errorMessage}`)
  }
}
```

**Flow:** restore: execute=false ⇒ '' without touching APIs; try exact-primary-with-fallback restore; miss ⇒ informational hint ("With cache the pipeline would be faster"); hit ⇒ return the MATCHED key as `reservedCacheKey`; API failure ⇒ warning + ''. Upload phase: skip when execution unsuccessful or default-branch-only gate says no (`isNeedToUploadCache`: useCaches&&defaultBranchOnly requires current ref === refs/heads/<default_branch>; misconfiguration warns) → skip when primaryKey===reservedCacheKey (restore already filled this exact cache; re-saving identical content wastes minutes) → saveCache with the 'already exists' race caught by MESSAGE STRING match → other errors warn only.
**Invariant:** The reserved-key comparison is load-bearing: because primary = additional+hash, a prefix-only fallback hit has different keys and SHOULD overwrite... except saves are keyed immutably — so the design lets the newer hash key save while the old entry ages out. The 'Cache already exists.' string match is brittle-by-necessity (the toolkit throws, doesn't return typed errors); porters must keep BOTH the pre-check AND the catch.
**Probe:** `scan/__tests__/utils.test.ts` :27-67 isNeedToUploadCache matrix (default branch true/false × useCaches × defaultBranchOnly + warning assertion). Network paths of restore/upload untested upstream (coverage caveat; pinned :394-484).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "saveCache restoreCaches reservedCacheKey", limit: 5 });
```

## Verdict
Adopt the three-layer skip ladder (gate → reserved-equality → already-exists-catch) for any immutable-key cache service; adapt the string-match to your client's error type if it has one; omit nothing else.
