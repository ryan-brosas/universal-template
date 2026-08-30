<!-- capsule-v2 -->
# Auto-lock-refresh expiry cancellation — what happens when a long sync outlives its own lease?

**Source:** joplin (AGPL-3.0) `dev@94911a86ff5dde7a8c5be112884373ad284ae7f6`; Codebase Memory `joplin`. **Question:** How does a client holding a TTL lock behave when refresh proves the lease was lost?

## Heartbeat + terminal expiry
**Path/Symbol:** `packages/lib/services/synchronizer/LockHandler.ts` :380-456 (`startAutoLockRefresh` / `stopAutoLockRefresh`); consumer wiring `packages/lib/Synchronizer.ts` :578-584.
**Signature:** `startAutoLockRefresh(lock: Lock, errorHandler: (error: Error) => void): string` returns handle key `${type}_${clientType}_${clientId}`.
**Data Shape:** per-handle `{ id, inProgress }` timer record keyed in `refreshTimers_`; interval default 60s vs lockTtl 180s (3× headroom).

### Decisive source
```ts
const locks = await this.locks(lock.type);
if (!hasActiveLock(locks, await this.currentDate(), this.lockTtl, lock.type, lock.clientType, lock.clientId)) {
    // If the previous lock has expired, we shouldn't try to acquire a new one...
    error = new JoplinError('Lock has expired', 'lockExpired');
} else {
    try { await this.acquireLock(lock.type, lock.clientType, lock.clientId); ... } catch (e) { error = e; }
}
if (error) { /* clearInterval + delete handle */ errorHandler(error); }
```
Consumer side (Synchronizer.start):
```ts
this.lockHandler().startAutoLockRefresh(syncLock, (error) => {
    logger.warn('Could not refresh lock - cancelling sync. Error was:', error);
    this.syncTargetIsLocked_ = true;
    void this.cancel();
});
```

**Flow:** tick → skip if previous tick still in flight (`inProgress` latch) → verify lock still active remotely → re-acquire (refresh timestamp) OR raise `lockExpired`/transport error → errorHandler tears down the timer itself and the synchronizer flips `syncTargetIsLocked_` so every subsequent `apiCall` rethrows `'lockError'` (apiCall wrapper :380-397) and `cancel()` unwinds the run.
**Invariants:** (1) an expired lease is TERMINAL — never silently re-acquired ("other clients might have performed operations that invalidate the current operation", e.g. target upgraded underneath you); (2) `inProgress` latch prevents overlapping refreshes; (3) handle map entries are checked again after every await because `stopAutoLockRefresh` may have fired mid-tick (defer() guards); (4) errorHandler is responsible for stopping the timer — double-stop tolerated (`stopAutoLockRefresh` no-ops on missing handle, deliberately not throwing since the error path already deleted it).
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/joplin && grep -cF "new JoplinError('"'"'Lock has expired'"'"', '"'"'lockExpired'"'"')" packages/lib/services/synchronizer/LockHandler.ts && grep -n "void this.cancel()" packages/lib/Synchronizer.ts | wc -l'` (anchored at repo root; expects `1` then ≥1 line containing `void this.cancel()` at :583).
**Trap:** `currentDate()` is REMOTE time (via `api_.remoteDate()` through temp-dir file mtimes) — comparing against local clock drifts with client clocks; porters substituting Date.now() break cross-device expiry.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joplin", query: "startAutoLockRefresh lockExpired refreshTimers cancel syncTargetIsLocked", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: heartbeat-with-terminal-expiry + cancellation-via-error-channel for any lease held across long jobs. Adapt intervals (keep ≥2× TTL headroom). Omit shim setInterval indirection.
