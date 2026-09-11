<!-- capsule-v2 -->
# Scheduler lease pump — how does one tick reconcile durable state without double-dispatching?

**Source:** dsh-factory MIT `main@3405edc7` (2026-08-24); Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How does a multi-process scheduler elect a leader and run claim/reconcile work each tick without two processes claiming the same ready task?

## Leader-elected single-flight pump
**Path/Symbol:** `packages/scheduler/src/index.ts` (`FactoryScheduler.pump`, `FactoryScheduler.schedulePump`) (:203–228).
**Signature:** `private schedulePump(): Promise<void>` / `private async pump(): Promise<void>`.
**Data Shape:** `pumping: Promise<void> | undefined` latch on the instance; config defaults `tickMs=1000`, `leaseTtlMs=10000`, `maxConcurrent=3`; events `factory/changed`, `agent/status`, `agent/error` plus a `setInterval(tickMs)` (unref'd) all funnel into `schedulePump()`.

### Decisive source
```ts
private schedulePump(): Promise<void> {
    if (this.stopped) return Promise.resolve()
    if (this.pumping !== undefined) return this.pumping
    this.pumping = this.pump().catch((error: unknown) => {
      this.ctx.logger.warn(`Factory scheduler reconciliation failed: ${this.message(error)}`)
    }).finally(() => { this.pumping = undefined })
    return this.pumping
}

private async pump(): Promise<void> {
    if (!await this.ctx.factory.acquireSchedulerLease(this.config.leaseTtlMs)) return
    await this.ctx.factory.activateDueAutomations()
    const snapshot = await this.ctx.factory.snapshot()
    await this.ctx.factory.requeueOrphanedRuns(
      new Set(snapshot.agents.map(agent => agent.sessionId)),
      new Set([...this.active.values()].map(active => active.runId)),
      this.config.maxAttempts,
    )
    await this.reconcileActive()
    const claims = await this.ctx.factory.claimReadyTasks(this.config.maxConcurrent)
    for (const claim of claims) this.start(claim)
    ...
}
```

**Flow:** timer/event → `schedulePump` (dedupe via promise latch) → `pump` → non-leaders return after `acquireSchedulerLease(leaseTtlMs)` → activate due automations → snapshot → requeue orphaned runs (live session ids minus own active run ids) → cancel cancelled tasks (`reconcileActive`) → `claimReadyTasks(maxConcurrent)` → start each claim → periodic sweep gate.
**Invariant:** The leader check happens INSIDE the pump before any mutation, and dispatch mutations re-check the lease inside the store transaction (`claimReadyTasks` passes `{ processId, now }` as the lease guard) — so a process that loses leadership between acquire and commit cannot write. Concurrent pumps collapse onto ONE shared promise; a new tick during a pump is dropped, not queued.
**Probe:** `packages/store-sqlite/tests/store.spec.ts` "elects one leader and permits takeover only after expiry" (second process acquiring before expiry gets the FIRST process back as leader; takeover only after `expires_at`). Deterministic: from the repo root, `grep -c 'acquireSchedulerLease' packages/scheduler/src/index.ts` = 1 and `grep -c 'BEGIN IMMEDIATE' packages/store-sqlite/src/index.ts` = 4 (all writes serialized under one immediate transaction).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "acquireSchedulerLease", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified live: rank-1 `FactoryDomain.acquireSchedulerLease packages/domain/src/index.ts 768-772`.)

## Verdict
Adopt the three-layer election contract: tick-level lease acquire + transaction-level lease guard + idempotent per-task `start()` skip. Adapt event names/timer wiring to the host scheduler framework. Omit cordis effect/drain plumbing specifics (host lifecycle).
