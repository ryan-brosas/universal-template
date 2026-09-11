<!-- capsule-v2 -->
# Watchdog settledGrace — the fifth timer that guarantees a hung teardown still dies

**Source:** billion-context-pi (MIT) `master@6a88c5565355baebccfaf27398a6008fe08619ed`; Codebase Memory project `mnt-hdd-utopia-inspo-billion-context-pi`. **Question:** The agent run is OVER (agent_settled fired) but the host process hasn't exited — what contract kills a genuinely hung teardown without racing normal exits?

## Settled ⇒ bounded grace ⇒ kill, idempotent and re-entrancy-safe
**Path/Symbol:** `src/delegate-watchdog.ts`: interface member (:34), timer var (:52), clear-on-dispose (:59), `settledGrace` implementation (:81-90); consumed by the delegate lifecycle at settle time (graceMs symmetric with `EOF_GRACE_MS` = 10s).
**Signature:** `settledGrace(graceMs: number, _killGraceMs: number, reason: string): void`.
**Data Shape:** one optional pending `settledGraceTimer`; no per-run bookkeeping — the guard state is just "already settled or timer already armed."
### Decisive source
```ts
// delegate-watchdog.ts:81-90 — note BOTH early-return guards and the
// clear-before-kill ordering inside the callback:
const settledGrace = (graceMs: number, _killGraceMs: number, reason: string): void => {
  if (hooks.isSettled() || settledGraceTimer) return;   // idempotent
  settledGraceTimer = setTimeout(() => {
    // Clear the reference before killing so a re-entrant killByWatchdog
    // (or a subsequent settledGrace call) sees no pending timer.
    settledGraceTimer = undefined;
    killByWatchdog(reason);
  }, graceMs);
  settledGraceTimer.unref?.();
};
```
**Flow:** pi emits agent_settled exactly ONCE in `_runAgentPrompt`'s finally — prompt + continue-loop + retries are all over and "the process should exit within milliseconds." If it's still alive after graceMs, something in teardown hangs (comment names a provider call not returning) and `killByWatchdog(reason)` fires. This closes the watchdog's coverage gap: its four original timers (idle, hard-cap, EOF-grace, dispose) all protect DURING a run; nothing protected AFTER settle until this landed.
**Invariant:** (1) Grace window symmetry is deliberate: normal exits are millisecond-level, so 10s only hits genuinely hung processes — do not shorten it or every slow GC/flush becomes a false kill. (2) Idempotence via double guard (`isSettled()` OR existing timer) means duplicate settle signals can't stack timers. (3) Clearing `settledGraceTimer = undefined` BEFORE calling kill prevents re-entrancy loops where the kill path itself triggers another watchdog evaluation. (4) `.unref()` keeps the timer from holding the event loop open — the watchdog must never be the reason a healthy process stays alive. (5) `dispose()` clears any pending grace timer (shutdown must not fire kills after cleanup began).
**Probe:** `cd $REFERENCE_ROOT/billion-context-pi && npx tsx --test tests/watchdog.test.ts` — GREEN at pin incl. the five pins (titles byte-verified at 6a88c556): "settledGrace does nothing when the run is already settled" (:138), "settledGrace is idempotent (only one timer is armed)" (:146), "dispose clears a pending settledGrace timer" (:157), "settle before the grace fires stops the kill (normal exit path)" (:165).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-billion-context-pi", query: "watchdog settledGrace killByWatchdog agent_settled", limit: 10 });
```

## Verdict
Adopt as an addition to any four-timer watchdog port: settle-time grace kill with idempotent arming, unref'd timers, clear-before-kill ordering, and symmetric-with-EOF-grace duration. Adapt the settle signal name to your host's run-finished hook. Omit the unused `_killGraceMs` parameter (reserved upstream).
