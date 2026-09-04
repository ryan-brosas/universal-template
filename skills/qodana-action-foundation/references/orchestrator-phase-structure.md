<!-- capsule-v2 -->
# Orchestrator phase structure — how are install/pull/scan/upload/comment phases ordered and parallelized, and what does each failure do to the exit code?

**Source:** qodana-action Apache-2.0 `main@829c6a56…`; Codebase Memory `qodana-action`. **Question:** What runs before/after the scanner, what is concurrent, and how does the exit code flow into job failure?

## Three-phase mains with Promise.all fans and exit-code-preserving setFailed
**Path/Symbol:** `scan/src/main.ts:main` (:62-121), `setFailed(message, exitCode)` (:45-49 sets process.exitCode then core.error); `gitlab/src/main.ts:main` (:24-61, console.error+process.exit(exitCode)); `vsts/src/main.ts:main` (:40-76, tl.setResult Failed).
**Signature:** `async function main(): Promise<void>` per app; shared `isExecutionSuccessful(exitCode)` over `QodanaExitCode {Success=0, FailThreshold=255}`.
**Data Shape:** Inputs from `getInputs()` (module-level memoized once).

### Decisive source
```ts
const restoreCachesPromise = restoreCaches(...)
await Promise.all([
  putReaction(token, ANALYSIS_STARTED_REACTION, ANALYSIS_FINISHED_REACTION),
  prepareAgent(inputs.args, inputs.nightlyVersion, inputs.useInstalledCli),
  restoreCachesPromise
])
const reservedCacheKey = await restoreCachesPromise
const exitCode = (await qodana(inputs)) as QodanaExitCode
const canUploadCache = isNeedToUploadCache(...) && isExecutionSuccessful(exitCode)
await Promise.all([
  pushQuickFixes(...),
  uploadArtifacts(...),
  uploadCaches(cacheDir, primaryCacheKey, reservedCacheKey, canUploadCache),
  publishOutput(exitCode === QodanaExitCode.FailThreshold, ..., isExecutionSuccessful(exitCode))
])
if (!isExecutionSuccessful(exitCode)) {
  setFailed(`qodana scan failed with exit code ${exitCode}`, exitCode)
} else if (exitCode === QodanaExitCode.FailThreshold) {
  setFailed(FAIL_THRESHOLD_OUTPUT, exitCode)
}
```

**Flow:** PHASE 1 (setup): mkdir results/cache dirs; concurrent reaction-start + agent-prep (CLI install + conditional image pull) + cache restore (promise held so its KEY can be reused after await). PHASE 2 (scan): single exec of `qodana scan --cache-dir --results-dir [--skip-pull] [args…] [--commit sha?]` with `NONINTERACTIVE=1` and `QODANA_REVISION` env; ignoreReturnCode so the code flows through. PHASE 3 (publish): concurrent quick-fixes push + artifact zip-upload + cache save-gated-on-success + output publication (comment/summary/checks) → final failure decision distinguishing generic failure vs FailThreshold(255) with dedicated message. Both non-scan apps mirror the phases minus reactions/checks; GitLab additionally copies caches to/from the user-visible `.qodana/cache` location BEFORE/AFTER (prepareCaches/uploadCache with resolve-equality skip guards, gitlab utils :369-413) and VSTS uploads SARIF as a `CodeAnalysisLogs` artifact for the Scans tab (:230-242). All three catch-all wrap main in setFailed(message, 1).
**Invariant:** Cache upload happens ONLY when `useCaches && execution successful` (and default-branch-only when configured — `isNeedToUploadCache` warns when cache-default-branch-only is set without use-caches); publishOutput receives `failedByThreshold = exitCode === 255` separately from `execute = isExecutionSuccessful` so a threshold-failure still publishes full results while a hard failure publishes nothing new. The reserved-key comparison (`primaryKey === reservedCacheKey` ⇒ skip upload) prevents redundant saves when restore hit the exact key.
**Probe:** `scan/__tests__/utils.test.ts` :27-67 pins isNeedToUploadCache matrix incl. the warning; arg assembly pinned by `scan/__tests__/main.test.ts` :85-93 (scan args order fixture). Mains themselves untested upstream (coverage caveat; pinned by ranges).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qodana-action", query: "main qodana scan uploadArtifacts publishOutput", limit: 8 });
```

## Verdict
Adopt the phase skeleton and the success-gated cache-save + threshold-aware publishing split; adapt platform APIs; omit reaction lifecycle if your host has no PR reactions.
