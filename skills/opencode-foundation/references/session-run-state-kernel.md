<!-- capsule-v2 -->
# Session run-state kernel — how are loop, shell, and cancel serialized per session?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** What prevents two loops or a shell+loop from interleaving on one session, and how does cancel cascade to background jobs?

## Runner registry with queued callers
**Path/Symbol:** `packages/opencode/src/session/run-state.ts` (whole file, 151L; `runner` :52–69; `cancelBackgroundJobs` :111–143).
**Signature:** `ensureRunning(sessionID, onInterrupt, work)` / `startShell(..., ready?: Latch)` / `assertNotBusy` / `cancel` — thin wrappers over a per-instance `Map<SessionID, Runner>` created in InstanceState scope.
**Data Shape:** Each session gets ONE `Runner` (from `@/effect/runner`) wired with `onIdle` (delete from map + status→idle), `onBusy` (status→busy), and the caller's `onInterrupt` fallback effect. Shell entry takes a `Latch` that shellImpl opens once message scaffolding is durably written; busy shells surface as typed `Session.BusyError`.

### Decisive source
```ts
// run-state.ts:118-142 — cancel fans out transitively through job metadata
const matches = (job: BackgroundJob.Info) => {
  if (job.status !== "running") return false
  if (cancelled.has(job.id)) return false
  if (pending.has(job.id)) return true
  if (typeof job.metadata?.sessionId === "string" && pending.has(job.metadata.sessionId)) return true
  return typeof job.metadata?.parentSessionId === "string" && pending.has(job.metadata.parentSessionId)
}
let batch = jobs.filter(matches)
while (batch.length > 0) {           // BFS wave: cancelling a job ENROLLS its ids as pending
  yield* Effect.forEach(batch, (job) => background.cancel(job.id).pipe(Effect.tap(() =>
    Effect.sync(() => {
      cancelled.add(job.id); pending.add(job.id)
      if (typeof job.metadata?.sessionId === "string") pending.add(job.metadata.sessionId)
    }))), { concurrency: "unbounded", discard: true })
  batch = jobs.filter(matches)       // re-filter so newly-linked jobs join the next wave
}
```

**Flow:** every entry path (`loop`, `shell`) funnels through runner-per-session → concurrent loop CALLERS queue on the same runner and all receive the SAME final assistant result → a second shell while one runs ⇒ BusyError; a loop while a shell runs WAITS until shell exits then proceeds → `cancel` first cancels matching BackgroundJobs (transitive closure over sessionId/parentSessionId), interrupts the runner (triggering its onInterrupt finalizer, e.g. finalizeInterruptedAssistant), and without any runner still resets status to idle.
**Invariant:** One-runner-per-session is the mutual-exclusion mechanism — status.busy/idle transitions are OWNED by runner lifecycle callbacks, never set ad hoc. The cancel fan-out must be iterative: a cancelled subagent job can itself have child jobs discovered only after the first wave.
**Probe:** `packages/opencode/test/session/prompt.test.ts:1710` "loop waits while shell runs" (0 LLM calls while shell active, 1 after); `:1747` "shell completion resumes queued loop callers" (two forked loops both succeed, same message id, 1 call total); `:1471/:1511` assertNotBusy/shell BusyError; `:1123` cancel resolves with assistant message; `:1959` cancel interrupts loop queued behind shell.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "session run state busy shell latch", limit: 8 });
```

## Verdict
Adopt runner-per-session mutual exclusion + transitive job-cancel waves + latch-gated shell readiness; adapt Runner/Latch to host concurrency primitives; omit BackgroundJob schema specifics.
