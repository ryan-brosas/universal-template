<!-- capsule-v2 -->
# Leading-edge throttle with trailing flush — how do I classify a burst once, but always against its FINAL state?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853f4bed28f7a0cca14dd1c02f54b86d6fa`; Codebase Memory `localterm`. **Question:** How do I coalesce a burst of filesystem events into exactly two classifications — first event and final state — without dropping the post-burst snapshot?

## Trigger → trailingPending → re-entrant flush
**Path/Symbol:** `packages/server/src/utils/throttle.ts:Throttle` (7–53); consumed per-repo by `automation-git-watcher.ts` (state.throttle.trigger at :248) and the per-session GitDiffWatcher.
**Signature:** `new Throttle(callback: () => void, intervalMs: number)`; `trigger(): void`; `reset(): void` (cancel pending trailing); `dispose(): void`.
**Data Shape:** `timer: NodeJS.Timeout | null`; `trailingPending: boolean`; `disposed: boolean`. Timers are unref'd.

### Decisive source
```ts
// :37-51 — the trailing flush RE-ENTERS trigger for ongoing bursts
trigger(): void {
  if (this.disposed) return;
  if (this.timer !== null) { this.trailingPending = true; return; }
  this.callback();
  this.timer = setTimeout(() => this.flush(), this.intervalMs);
  this.timer.unref?.();
}
private flush(): void {
  this.timer = null;
  if (!this.trailingPending) return;
  this.trailingPending = false;
  // Re-enter trigger so a burst that's still ongoing starts a fresh window
  // rather than collapsing to a single trailing flush.
  this.trigger();
}
```

**Flow:** first `trigger()` after quiet runs the callback IMMEDIATELY (low latency for burst start). Calls inside the window only set `trailingPending`. When the window elapses, if anything was pending the callback runs again — via re-entering `trigger()`, so a still-ongoing burst opens a fresh window instead of collapsing everything into one trailing call. `reset()` cancels without running (stop/restart paths so a stale callback can't fire into new state); `dispose()` latches.
**Invariant:** the FINAL state of a burst is always classified — a leading-edge-only throttle would leave consumers reading a mid-burst snapshot (e.g. a partial write before an atomic rename). Exactly one leading + one trailing run per burst window; never more than one callback in flight (single timer).
**Probe:** `packages/server/tests/throttle.test.ts` (7 tests, fake timers — leading-edge immediate fire, trailing flush after burst, reset cancellation).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "Throttle trigger trailingPending flush", limit: 5, detail: "compact" });
```

## Verdict
Adopt verbatim (~45 lines) anywhere fs/FSWatcher bursts must collapse to first+last classification; adapt the interval to host latency budgets; nothing to omit. Pinned by 7 direct tests at this commit.
