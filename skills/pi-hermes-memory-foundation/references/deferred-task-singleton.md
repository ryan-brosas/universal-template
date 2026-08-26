<!-- capsule-v2 -->
# Deferred-task singleton — startup work that outlives its trigger without blocking or racing shutdown

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory` (full-tree index). **Question:** How do you schedule heavy startup work (parsing hundreds of session JSONL files into SQLite) from an event handler WITHOUT blocking that handler's resolution, WITHOUT double-running, and WITHOUT the process exiting mid-write at shutdown?

## scheduleSessionBackfill
**Path/Symbol:** `src/handlers/session-backfill.ts:scheduleSessionBackfill` (:60–111); `waitForSessionBackfill` (:119–139); constants `SESSION_BACKFILL_SHUTDOWN_TIMEOUT_MS = 5000` (:9), `SESSION_BACKFILL_MAX_FILES = 50` (:10); module-singleton `sessionBackfillState { inProgress, promise }` (:22–25).
**Signature:** `scheduleSessionBackfill(dbManager, sessionsDir, options?) → boolean` (true = scheduled, false = skipped); `waitForSessionBackfill(timeoutMs?) → Promise<boolean>` (true = finished/idle, false = timed out).
**Data Shape:** every collaborator is injectable via `options` (`state`, `setTimeoutFn`, `needsBackfillFn`, `indexSessionsFn`, `maxFilesToIndex`, `touchBackfillTimestampFn`, `notify`) — the whole scheduler is testable without fake timers on globals.

### Decisive source
```ts
if (state.inProgress) return false;              // re-entrancy gate FIRST
try {
  if (!needsBackfillFn(dbManager, sessionsDir))  // cheap pre-check outside the task
    return false;
} catch (err) {
  notifyBestEffort(options.notify, `⚠️ Session backfill check failed: …`, 'warning');
  return false;                                  // a broken CHECK never schedules
}
state.inProgress = true;
state.promise = new Promise<void>((resolve) => {
  setTimeoutFn(() => {                           // DEFER: session_start resolves first
    try {
      const result = indexSessionsFn(dbManager, sessionsDir, { maxFilesToIndex });
      if (!result.reachedLimit) touchBackfillTimestampFn(dbManager);
      // ^ timestamp advances ONLY on a complete pass, so a capped pass retries next boot
      notifyBestEffort(options.notify, formatBackfillResult(result),
        result.errors.length > 0 || result.reachedLimit ? 'warning' : 'info');
    } catch (err) { notifyBestEffort(/* warning */); }
    finally { state.inProgress = false; state.promise = null; resolve(); }
  }, 0);
});
return true;
```

**Flow:** (1) caller (the `session_start` handler in `index.ts:205-216`) invokes the scheduler; (2) the in-progress flag makes repeat events no-ops; (3) `needsBackfill` is probed inside its own try/catch so a corrupted DB degrades to "don't schedule" plus a warning, never a crash during startup; (4) the actual parse runs on a `setTimeout(…, 0)` tick so the synchronous part of the handler returns immediately; (5) at shutdown `waitForSessionBackfill` races the stored promise against a timer.
**Invariant:** the shutdown wait NEVER cancels the task — `Promise.race([promise.then(() => true), timeout])` just stops waiting; a `false` return means "still running", not "failed". The backfill timestamp advances only when the pass was NOT cut off by the file cap (`reachedLimit`), which is what makes a capped startup resume instead of skipping forever. `notifyBestEffort` wraps every notification in try/catch — notification failures can never affect the backfill.
**Probe:** `tests/handlers/session-backfill.test.ts` — asserts scheduling returns true once then false while in progress, defers via injected `setTimeoutFn`, does not advance the backfill timestamp when `reachedLimit`, and `waitForSessionBackfill` resolves false after the injected timeout with the task still pending. Coverage caveat: tests/ excluded from the graph index; probes named from on-disk test files.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "scheduleSessionBackfill waitForSessionBackfill sessionBackfillState", limit: 5 })`

## Verdict
Adopt the pattern: module-singleton `{inProgress, promise}` + `setTimeout(0)` deferral + bounded work + timestamp-advance-only-on-complete + race-not-cancel shutdown wait, with every dependency injected through options. Adapt the constants (5 s shutdown budget, 50-file cap) and the notification strings. Omit nothing — the twin file `session-live-index.ts` shows the same skeleton with a different delay and coalescing semantics (see live-index-coalescing-window.md).
