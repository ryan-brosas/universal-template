<!-- capsule-v2 -->
# Live-index coalescing window — indexing a stream that is still being appended by another writer

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** A host fires `message_end` BEFORE it persists the finalized message to the JSONL session file — how do you index every message exactly once without reading half-written data or queueing per-event?

## scheduleLiveSessionIndex
**Path/Symbol:** `src/handlers/session-live-index.ts:scheduleLiveSessionIndex` (:37–69); `waitForLiveSessionIndex` (:71–91); `SESSION_LIVE_INDEX_DELAY_MS = 50` (:4); `SESSION_LIVE_INDEX_SHUTDOWN_TIMEOUT_MS = 5000` (:5); `withCorruptionRecovery` wrap (:55).
**Signature:** `scheduleLiveSessionIndex(dbManager, sessionManager, options?) → boolean`; options: `state`, `setTimeoutFn`, `indexLiveSessionFn`, `delayMs`, `onError`.
**Data Shape:** `SessionManagerSnapshot = Parameters<typeof indexLiveSession>[1]` — the scheduler captures the manager object itself, not a copy; the delayed task reads whatever the host has persisted BY THEN.

### Decisive source
```ts
/**
 * Pi emits message_end before it appends the finalized message to the JSONL
 * session file/session manager. Deferring briefly lets Pi persist the entry
 * first, then we index any message ids not already present in SQLite. Multiple
 * message_end events in the same window coalesce into one all-missing sync.
 */
export function scheduleLiveSessionIndex(dbManager, sessionManager, options = {}): boolean {
  const state = options.state ?? sessionLiveIndexState;
  if (state.inProgress) return false;        // ← THE COALESCER: event N+1 in the
                                              //   same window is dropped, not queued
  state.inProgress = true;
  state.promise = new Promise<void>((resolve) => {
    setTimeoutFn(() => {
      try {
        dbManager.withCorruptionRecovery(() => {
          indexLiveSessionFn(dbManager, sessionManager);   // id-sync: indexes only
        });                                                 // ids missing in SQLite
      } catch (err) {
        try { options.onError?.(err); } catch { /* best effort */ }
      } finally {
        state.inProgress = false; state.promise = null; resolve();
      }
    }, delayMs);                               // 50 ms persistence window
  });
  return true;
}
```

**Flow:** (1) every `message_end` calls the scheduler (`index.ts:297-301`); (2) the first event in a 50 ms window flips the flag and schedules the sync; (3) later events during the window hit `inProgress` and are silently absorbed — correctness comes from the sync being ALL-MISSING (it diffs message ids against SQLite), so absorbing events loses nothing; (4) the sync runs under `withCorruptionRecovery` so a damaged DB triggers rebuild/recreate instead of throwing per message.
**Invariant:** the delay is load-bearing ORDERING (host-persist-before-read), not throttling cosmetics; dropping events is safe ONLY because the worker reconciles by id-set, never by event payload; errors route to `onError` (console.warn in production), never to the caller.
**Probe:** `tests/handlers/session-live-index.test.ts` — asserts the second call during the window returns false, the injected delay elapses before `indexLiveSession` runs, and errors surface through `onError` without rejecting. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "scheduleLiveSessionIndex indexLiveSession sessionLiveIndexState", limit: 5 })`

## Verdict
Adopt the coalescing window whenever you mirror an append-only log into a queryable store from emitter callbacks that fire pre-persistence. Adapt the 50 ms delay to the host's persistence timing. Compare with `deferred-task-singleton.md` (same skeleton): backfill uses `setTimeout(0)` + a completeness timestamp because it is a batch job; live indexing uses a longer window + id-set reconciliation because it rides a live stream.
