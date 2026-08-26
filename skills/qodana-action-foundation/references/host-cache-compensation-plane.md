<!-- capsule-v2 -->
# Host cache compensation plane — how do you approximate actions/cache on platforms that have no cache primitive?

**Source:** qodana-action Apache-2.0 `main@e0675fbe…`; Codebase Memory `qodana-action`. **Question:** GitHub has @actions/cache; Azure DevOps and GitLab CI (as used here) do not. What does each host substitute, and what guards keep the substitution honest?

## GitLab's user-visible mirror vs VSTS's nothing
**Path/Symbol:** `gitlab/src/utils.ts:getInitialCacheLocation` (:369-374), `prepareCaches` (:377-392), `uploadCache` (:394-413); wiring `gitlab/src/main.ts` (:29 prepareCaches BEFORE prepareAgent, :46-51 uploadCache after publish); contrast `vsts/src/main.ts` (NO cache calls at all) and scan's restoreCaches/uploadCaches (cache-save-skip-contract).
**Signature:** `prepareCaches(cacheDir): void` / `uploadCache(cacheDir, execute: boolean): void`; location = `getQodanaStringArg('CACHE_DIR', ${CI_PROJECT_DIR}/.qodana/cache)`.
**Data Shape:** plain directories; sync `fs.cpSync(..., {recursive:true[, force:true]})`; no keys, no compression, no network.

### Decisive source
```ts
// gitlab/src/utils.ts
if (path.resolve(initialCacheLocation) == path.resolve(cacheDir)) {
  debug(`Initial cache location matches cacheDir (${cacheDir}); skipping copy`)   // guard BOTH directions
  return
}
if (fs.existsSync(initialCacheLocation)) {
  fs.cpSync(initialCacheLocation, cacheDir, {recursive: true})                    // before scan
} 
// uploadCache:
fs.cpSync(cacheDir, initialCacheLocation, {recursive: true, force: true})         // after scan, overwrite-mirror
```

**Flow:** GitLab persists whatever a job leaves under `.qodana/` between pipelines (its real persistence channel), so prepareCaches copies the persisted cache INTO the working cacheDir before install/pull/scan, and uploadCache mirrors cacheDir back with force AFTER publishing. The resolve-equality skip prevents self-copy when CACHE_DIR was pointed at the working dir. Gate differs from GitHub: `useCaches && (Success || FailThreshold)` inline in main (:48-50) — isExecutionSuccessful inlined, no default-branch concept. VSTS simply opts out entirely: its main never restores or saves caches.
**Invariant:** The comment at :376 is the contract: "at this moment any changes inside .qodana dir may affect analysis results" — the mirror exists so users can inspect/carry caches, so it must be consistent BEFORE analysis starts and refreshed only AFTER results are published; equality guards are what stop the mirror from corrupting a live run.
**Probe:** EXECUTED at pin: gitlab suite **2 passed** (summary fixtures only); no upstream test drives prepareCaches/uploadCache (fs/env-heavy) — pinned by ranges + anchors (coverage caveat). Deterministic anchor: `grep -n "may affect analysis results" gitlab/src/utils.ts` → :376.
**Coverage caveat:** none — cited paths no_recorded_issue, generation matches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "prepareCaches uploadCache initialCacheLocation qodana cache mirror", limit: 6 });
```
(rank-1 `gitlab.src.utils.uploadCache` :394-413, rank-2 `prepareCaches` :377-392 at execution time.)

## Verdict
Adopt "compensate for missing cache primitives with an explicit filesystem mirror guarded by resolve-equality checks both directions"; adapt the persistence channel (GitLab artifact dirs, workspace volumes, S3 mounts) and the success gate to your platform; omit nothing structural — the before-copy / after-force-mirror ordering IS the port.
