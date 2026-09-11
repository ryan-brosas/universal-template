<!-- capsule-v2 -->
# Run lifecycle — how does a claimed task become a bound Agent session and settle exactly once?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I execute a claimed task as an Agent run with crash-safe settlement, without losing a failure or double-settling?

## executeClaim → monitor → settlement funnel
**Path/Symbol:** `packages/scheduler/src/index.ts` (`FactoryScheduler.start`, `executeClaim`, `monitor`) (:230–309) + `packages/domain/src/index.ts` (`finishRun`, `failRun`, `markRunWaiting`) (:841–903).
**Signature:** `private start(claim: FactoryTaskClaim): void` / `private async executeClaim(claim, active): Promise<void>` / `finishRun(runId, report: FactoryRunSettlement)`.
**Data Shape:** `ActiveRun { taskId, runId, done, handle?, channel?, lastError?, notify }`; claims are `{ task, project, run }` triples cloned out of the committed document; settlement report `{ outcome: succeeded|failed|blocked, summary, details?, artifacts? }` enriched with `mutations`.

### Decisive source
```ts
active.done = this.executeClaim(claim, active).catch(async (error: unknown) => {
    this.ctx.logger.warn(`Factory ${claim.task.identifier} failed to execute: ${this.message(error)}`)
    try { await this.ctx.factory.failRun(claim.run.id, error) } catch (settleError: unknown) {
      this.ctx.logger.error(`Factory ${claim.task.identifier} failure could not be persisted: ...`)
    }
}).finally(async () => {
    active.notify?.()
    if (active.handle !== undefined) await active.handle.dispose()
    this.active.delete(claim.task.id)
    if (!this.stopped) void this.schedulePump()
})
```

**Flow:** claim → allocate checkout lane → optional setup command (nonzero exit/signal → throw → failRun) → resolve model selection → create Agent session `factory-<runId>` with preset+model+completion tool → `bindRun(runId, agentId, checkoutPath)` → followup task content → monitor loop (`whenIdle` → stopped→markRunWaiting / lastError→failRun / report→flush session + finishRun; blocked keeps the node nonterminal and loops) → optional cleanup on `remove-succeeded`. Every domain settlement mutates through `expectOwnedRun`: if `task.activeRunId !== run.id` or the run left dispatching/running/waiting, it returns NO-CHANGE — settlement is idempotent.
**Invariant:** A thrown error anywhere in execution is persisted by the `.catch` → `failRun`, and `.finally` always disposes the handle, deletes the active entry, and RE-ARMS the pump — a failed claim can never wedge the scheduler or leave an orphan promise. The scheduler never infers completion from intent; only an explicit channel report settles success.
**Probe:** `packages/scheduler/tests/scheduler.spec.ts` "runs a recurring task through a real DSH Agent and returns it to Scheduled with a Triage result" (run reaches `succeeded`, task returns to `scheduled`, `sessionId` matches `/^factory-/`). Deterministic from repo root: `grep -c 'whenIdle' packages/scheduler/src/index.ts` = 1; `grep -c 'expectOwnedRun' packages/domain/src/index.ts` = 5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "claimReadyTasks", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified live: rank-1 `FactoryDomain.claimReadyTasks packages/domain/src/index.ts 793-824`.)

## Verdict
Adopt the catch-persist/finally-rearm settlement funnel and the ownership-checked idempotent settlement guards. Adapt Agent creation/preset mounting to the host agent runtime. Omit cordis parallel-event flush semantics (host-specific).
