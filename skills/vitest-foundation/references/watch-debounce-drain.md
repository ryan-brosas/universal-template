<!-- capsule-v2 -->
# Watch rerun debounce drain — how do rapid successive file changes collapse into ONE partial rerun without losing a change or racing a restart?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How does the watch loop coalesce bursts of watcher events into a single `runFiles` call, and what state must be captured before/after the awaits?

## Vitest.scheduleRerun timer + epoch guard
**Path/Symbol:** `packages/vitest/src/node/core.ts:Vitest.scheduleRerun` (:1421–1482); `WATCHER_DEBOUNCE = 100` (:63); set membership at :196 (`watcher.onWatcherRerun(file => scheduleRerun(file))`).
**Signature:** `private async scheduleRerun(triggerId: string): Promise<void>`; body schedules `setTimeout(..., WATCHER_DEBOUNCE)`.
**Data Shape:** `_rerunTimer: any` (single pending timer handle); `restartsCount` epoch; reads+clears shared `watcher.changedTests`; optional `filenamePattern` filter; emits `onWatcherRerun` then delegates to `runFiles(specs, false)`.

### Decisive source
```ts
const currentCount = this.restartsCount   // 1) capture BEFORE awaiting
clearTimeout(this._rerunTimer)
await this.cancelPromise
await this.runningPromise                 // previous run fully settles first
clearTimeout(this._rerunTimer)

this._rerunTimer = setTimeout(async () => {
  if (this.closingPromise) return
  if (this.watcher.changedTests.size === 0) {
    this.watcher.invalidates.clear()      // nothing to run => drop invalidations too
    return
  }
  if (this.restartsCount !== currentCount) return   // 2) stale after restart
  this.isFirstRun = false
  this.snapshot.clear()
  let files = Array.from(this.watcher.changedTests)
  if (this.filenamePattern) {
    const filteredFiles = await this.globTestSpecifications(this.filenamePattern)
    files = files.filter(file => filteredFiles.some(f => f.moduleId === file))
    if (files.length === 0) return        // changed file not in current pattern scope
  }
  this.watcher.changedTests.clear()       // snapshot THEN clear (no lost-change window for later adds)
  ...
  await this.runFiles(specifications, false)
  await this.report('onWatcherStart', this.state.getFiles(files))
}, WATCHER_DEBOUNCE)
```

**Flow:** every watcher callback calls `scheduleRerun(file)` → prior timer cleared (burst = one trailing timer) → waits for cancel + running promise → 100 ms later snapshots `changedTests`, applies filename-pattern filter, clears the set, converts files→specs via `getModuleSpecifications` (+ user `_onFilterWatchedSpecification` filters), reports `onWatcherRerun(files, triggerLabel)` with the RELATIVE trigger path, runs, reports `onWatcherStart`.
**Invariant:** three guards must survive porting: (1) trailing-edge single timer (leading-edge would run mid-burst with a partial set), (2) `restartsCount` re-check INSIDE the timer callback — an awaited restart invalidates the scheduled closure, (3) `changedTests` is snapshotted via `Array.from` BEFORE `.clear()` while `runFiles` itself is single-flight — files added during the run simply wait for the next timer instead of being dropped. Also note `invalidates.clear()` on the empty-set early exit: invalidated modules with no affected tests must not leak into the NEXT run.
**Probe:** `test/e2e/test/watch/file-watching.test.ts` — burst-tolerance is observable as exactly one `RERUN` per settled edit (:55–63, :111–119); `global-setup-rerun.test.ts` pins that editing a globalSetup file triggers `RERUN` of dependent suites (:45–52).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "scheduleRerun", limit: 5, fields: ["signature", "name", "file"] });
```
(Graph resolves BOTH `VitestWatcher.scheduleRerun` (fan-out to handlers) and `Vitest.scheduleRerun` (debounce) — port both halves.)

## Verdict
Adopt the trailing-edge debounce + epoch guard + snapshot-then-clear pattern for any watch-driven incremental runner. Adapt the debounce constant and the spec-conversion step. Omit the filename-pattern filter unless your host has interactive filter state.
