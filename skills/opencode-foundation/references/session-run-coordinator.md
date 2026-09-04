<!-- capsule-v2 -->
# Session run coordinator — how do you serialize execution per session key while coalescing wakeups, joining concurrent callers, and surviving interruptions without losing newly recorded work?

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** A durable session engine records prompts (wake) and must run at most one drain per session at a time, let explicit resumes join the active drain, coalesce N mid-run wakeups into one follow-up, and guarantee that work recorded during interruption cleanup still runs — all without stack overflow on deep self-wake chains.

## Per-key serialization with coalesced wakes
**Path/Symbol:** `packages/core/src/session/run-coordinator.ts` (`make` :24-104, Entry :17-22, `start` :37-49, `settle` :51-65, `run` :67-79, `wake` :81-92, `interrupt` :94-101).
**Signature:** `make<Key,E>({drain: (key, force) => Effect<void,E>}) → Effect<Coordinator<Key,E>, never, Scope>`; `Coordinator = {active: Effect<ReadonlySet<Key>>, run: (key) => Effect<void,E>, wake: (key) => Effect<void>, interrupt: (key) => Effect<void>}`.
**Data Shape:** Entry = `{done: Deferred<void,E>, owner?: Fiber, pendingWake: boolean, stopping: boolean}`; `active: Map<Key, Entry>`; drains fork into a FiberSet owned by the coordinator scope.

### Decisive source
```ts
// run-coordinator.ts:37-49 — successor starts trampoline via yieldNow instead of a ready gate
const start = (key, entry, force, successor = false) => {
  const ready = Deferred.makeUnsafe<void>()
  const owner = fork(
    (successor ? Effect.yieldNow : Deferred.await(ready)).pipe(
      Effect.andThen(Effect.suspend(() => options.drain(key, force))),
      Effect.onExit((exit) => Effect.sync(() => settle(key, entry, exit))),
      Effect.exit, Effect.asVoid,
    ),
  )
  entry.owner = owner
  if (!successor) Deferred.doneUnsafe(ready, Effect.void)
}
// run-coordinator.ts:51-65 — settle: same-entry successor on clean wake, new-entry successor otherwise
const settle = (key, entry, exit) => {
  if (Exit.isSuccess(exit) && !entry.stopping && entry.pendingWake) {
    entry.pendingWake = false
    start(key, entry, false, true)
    return
  }
  const successor = entry.pendingWake ? makeEntry() : undefined
  if (successor === undefined) active.delete(key)
  else { active.set(key, successor); start(key, successor, false, true) }
  Deferred.doneUnsafe(entry.done, exit)
}
// run-coordinator.ts:67-79 — run joins, never starts twice
const run = (key) => Effect.uninterruptibleMask((restore) => {
  const entry = active.get(key)
  if (entry !== undefined) {
    if (entry.stopping) return restore(Deferred.await(entry.done).pipe(Effect.andThen(run(key))))
    return restore(Deferred.await(entry.done))
  }
  const next = makeEntry(); active.set(key, next); start(key, next, true)
  return restore(Deferred.await(next.done))
})
```

**Flow:** `run(key)` under uninterruptibleMask: existing entry → join its done (if stopping, await done THEN re-run to pick up the successor started during cleanup); no entry → create + start(force=true) + join. `wake(key)` is pure sync: an active entry gets pendingWake=true (N wakes coalesce into ONE follow-up); an idle key starts a force=false drain. `settle` runs on every drain exit: success + not stopping + pendingWake → reset the flag and start a successor on the SAME entry (original joiners see the original done Deferred); failure/defect/stopping → create a NEW entry when pendingWake (successor), else delete the key; then complete done with the exit. `interrupt`: no-op when idle (no owner); else stopping=true, CLEAR pendingWake, Fiber.interrupt(owner). A wake registered DURING interruption cleanup still runs: settle sees the fresh pendingWake on the now-stopping entry and starts a successor. `start()` forks into the FiberSet; non-successor starts gate the drain body behind a ready Deferred completed synchronously right after fork (defers the drain out of the caller's stack frame); successor starts use `Effect.yieldNow` — the trampoline that keeps deep synchronous self-wake chains off the call stack.

**Invariant:** At most one drain per key at a time; concurrent run() callers join the same drain; N wakes during an active drain produce exactly one follow-up; a wake registered during interruption cleanup still drains; interrupting a joined waiter never cancels the owner fiber; 20,000 synchronous self-wakes complete without stack overflow.
**Probe:** `packages/core/test/session-run-coordinator.test.ts` (read whole, 418L): "joins concurrent resumes for one key" pins runs===1; "coalesces wakes received during active execution" pins 3 wakes → runs===2; "runs again when woken during the follow-up" pins runs===3; "interrupts active execution and clears its pending wake" pins interrupts-only exit + empty active + runs===1; "runs a wake registered during interruption cleanup" pins runs===2; "starts a resume registered during interruption cleanup" pins forces [false,true]; "does not cancel execution when a joined waiter is interrupted" pins runs===1; "trampolines synchronous self-waking execution" pins runs===20_000. Source pin:
```bash
grep -n 'pendingWake' packages/core/src/session/run-coordinator.ts     # expect 7
grep -n 'Effect.yieldNow' packages/core/src/session/run-coordinator.ts # expect 1
```

## Execution routing + drain isolation
**Path/Symbol:** `packages/core/src/session/execution.ts` (Interface :9-16, noopLayer :26-34) + `packages/core/src/session/execution/local.ts` (layer :10-40).
**Signature:** `SessionExecution = {active, resume(sessionID), wake(sessionID), interrupt(sessionID)}`; local drain = store.get → die if missing → SessionRunner.run({sessionID, force}) provided the Location's service map.
**Data Shape:** noopLayer = all-void implementation for callers that only need durable recording (wake is a documented no-op).

### Decisive source
```ts
// execution/local.ts:16-24 — drain failures are logged, never propagated to wakers
drain: Effect.fnUntraced(function* (sessionID, force) {
  const session = yield* store.get(sessionID)
  if (!session) return yield* Effect.die(`Session not found: ${sessionID}`)
  return yield* SessionRunner.Service.use((runner) => runner.run({ sessionID, force })).pipe(
    Effect.provide(locations.get(session.location)),
    Effect.tapCause((cause) => Cause.hasInterruptsOnly(cause)
      ? Effect.void
      : Effect.logError("Failed to drain Session", cause).pipe(Effect.annotateLogs({ sessionID }))),
  )
}),
```

**Flow:** The coordinator's drain loads the session (die if gone), resolves the Location-scoped service map, and runs the runner; tapCause swallows interrupts-only causes and logs everything else with the sessionID annotation. Because wake() is pure sync (flag-set or fork), recording a prompt can never fail because of the executor; drain outcomes surface only to run() joiners and the log. The interface comment pins the routing intent: "Routes execution from a Session ID to the runner owned by that Session's Location" — future remote placement belongs in this file, not in callers.

**Invariant:** wake is infallible by construction; drain errors are observable (log) but contained; the noop layer makes recording-only deployments a wiring choice, not a code branch.
**Probe:** session-run-coordinator.test.ts "cleans active executions when its scope closes" pins scope-finalizer cleanup of in-flight drains; "snapshots only active executions" pins active-set membership transitions across two keys. Source pin:
```bash
grep -n 'noopLayer' packages/core/src/session/execution.ts  # expect 1
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "SessionRunCoordinator make settle pendingWake successor SessionExecution wake interrupt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the entry/successor algebra as the general kernel for per-key serialized execution with coalesced follow-ups: one Deferred per logical run, a boolean wake flag, a stopping latch, and a settle-time decision (same-entry successor on clean wake vs new entry after failure/interruption). Adopt the yieldNow trampoline for successor starts — any design where settle can synchronously re-start must keep the restart off the call stack or deep self-wake chains overflow. Adopt join-semantics run() (callers share the active drain; stopping callers re-run after cleanup) and infallible wake(). Adapt the Location service-map resolution to your own placement model; omit the noopLayer if every deployment executes. Direct test read whole (session-run-coordinator.test.ts 418L); bun runner blocked at this checkout (no node_modules), probes are byte-exact greps.
