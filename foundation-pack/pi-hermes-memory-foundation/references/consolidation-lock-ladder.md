<!-- capsule-v2 -->
# Consolidation lock ladder — contended-reload short-circuit, decoupled stale timeout, and deferred-is-not-failure semantics

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** When memory overflows and an LLM consolidation must run — possibly from several sessions at once — how do you prevent duplicate compression passes without failing the user's write that triggered it?

## triggerConsolidation + acquireConsolidationLock
**Path/Symbol:** `src/handlers/auto-consolidate.ts:triggerConsolidation` (:178–287), `acquireConsolidationLock` (:85–134); constants (:45–53): `CONSOLIDATION_LOCK_STALE_MS = 45_000`, `CONSOLIDATION_LOCK_HEARTBEAT_MS = 10_000`, `CONSOLIDATION_LOCK_WAIT_MS = 5_000`, `CONSOLIDATION_LOCK_POLL_MS = 50`; lock key builder `consolidationLockKey` (:75–78).
**Signature:** `triggerConsolidation(pi, store, target, signal?, timeoutMs?, toolTarget?, llmConfig?, directCtx?, dbManager?, projectName?, deps?) → ConsolidationResult { consolidated, deferred?, error? }`; `acquireConsolidationLock(store, target, toolTarget) → { lock | null, contended, waitedMs }`.
**Data Shape:** lock key = `sanitize(toolTarget):sanitize(target):sha256(storageIdentity)` — scoped per target AND per backing-file identity; the lease is an `AtomicLockCoordinator` lease (see atomic-lock-coordinator.md) with a `setInterval` heartbeat attached.

### Decisive source
```ts
// staleMs is deliberately decoupled from the consolidation timeout. The holder
// beats every CONSOLIDATION_LOCK_HEARTBEAT_MS while its child runs, so a
// legitimately slow consolidation (up to 2x timeoutMs once retryWithoutOverrides
// fires) never loses its lease, while a holder that stops making progress is
// reclaimable after seconds instead of after its worst-case runtime (#144).
const CONSOLIDATION_LOCK_STALE_MS = 45_000;

// Contention is usually transient. Poll for the lock … instead of hard-failing
// the memory write that triggered auto-consolidation on the very first collision.
const CONSOLIDATION_LOCK_WAIT_MS = 5_000;

let lock = null;
try {
  const attempt = await acquireConsolidationLock(store, target, toolTarget);
  lock = attempt.lock;
  if (!lock) {
    // Not a failure: the work is already running in another session. Say so
    // plainly so the memory-write path can ask for a retry instead of
    // reporting a broken consolidation mid-task (#144).
    return { consolidated: false, deferred: true,
             error: `Consolidation already in progress for target '${toolTarget}' in another session…` };
  }

  let promptEntries = entries;
  if (attempt.contended) {
    // We queued behind another session's consolidation and it has now finished.
    // If it already freed space, running a second LLM pass here costs a child
    // turn and over-compresses memory for nothing — hand the caller a
    // reload-and-retry instead.
    await store.loadFromDisk();
    const refreshed = entriesForTarget(store, target);
    if (refreshed.join(ENTRY_DELIMITER).length < currentContent.length)
      return { consolidated: true };        // someone else did the job — report success
    promptEntries = refreshed;              // else consolidate the FRESH entries
  }
  const result = await execChildPrompt(pi, buildConsolidationPrompt(target, toolTarget, promptEntries),
                                       llmConfig, { signal, timeoutMs, retryWithoutOverrides: true });
```

**Flow:** (1) direct in-process transport is tried first when `directCtx` exists — but unlike review/flush, an EMPTY result here (`appliedCount === 0`) is FAILURE (consolidation must free space) and falls through to subprocess; (2) subprocess path takes the cross-process lock with bounded polling; (3) losing the wait returns `deferred: true`, which callers translate into "retry shortly" rather than an error toast; (4) winning after contention re-reads disk and short-circuits success if the winner already shrank the content; (5) the heartbeat renews the lease every 10 s and is `.unref()`ed so it never holds the process open.
**Invariant:** `staleMs (45 s)` ≠ `timeoutMs (default 180 s)` — liveness comes from the heartbeat, not from the runtime budget, so slow-but-alive holders are safe and dead holders are reclaimed in seconds. A failed release/COMMIT must never fail the operation it protected. Contended winners MUST reload from disk before deciding — consolidating stale pre-contention entries would double-compress fresh data.
**Probe:** `tests/handlers/auto-consolidate.test.ts` — asserts contended runs short-circuit when content shrank, deferred results carry `deferred: true`, heartbeat renewal keeps the lease past staleMs during a long child run, and direct-mode empty results fall back to subprocess. Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "triggerConsolidation acquireConsolidationLock CONSOLIDATION_LOCK_STALE_MS", limit: 5 })`

## Verdict
Adopt the ladder: poll-don't-fail acquisition → explicit deferred outcome → contended-reload short-circuit → heartbeat-decoupled staleness. Adapt constants/env overrides (`PI_HERMES_CONSOLIDATION_LOCK_DIR/_WAIT_MS`). Pair with `markdown-mutation-lock.md` (shorter wait, throw-not-defer because a mutation cannot be deferred).
