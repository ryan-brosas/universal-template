<!-- capsule-v2 -->
# Agenda automation pump — how do you auto-approve and auto-start queued work with capacity limits, provenance vetoes, and mid-flight policy aborts?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** when a user flips a scope to `auto_start`, what prevents runaway loops, hand-authored files self-executing, or a policy change racing an in-flight pump?

## Single-flight microtask pump
**Path/Symbol:** `sdk/packages/core/src/tasks/agenda-task-manager.ts:1224-1239` (`queueAutomation`, callers=9), :1241-1311 (`pumpAutomation`), :1313-1332 (`canAutomaticallyApprove`), :1334-1347 (`taskChainDepth`).
**Signature:** `queueAutomation(scopeKey?)` enqueues scope keys and defers via ONE `queueMicrotask` guarded by the `automationPumping` latch; `pumpAutomation(): Promise<void>` drains the set.
**Data Shape:** state = `queuedAutomationScopes: Set<string>`, `automationPumping: boolean`, `automationPolicyGeneration: number` (bumped on every policy write), policy `{mode, applyToAgentCreated, maxConcurrentRuns, maxStartsPerHour, maxChainDepth, scopeKey}`.

### Decisive source
```ts
if (this.disposed || this.automationPumping) return;
this.automationPumping = true;
const policyGeneration = this.automationPolicyGeneration;   // latch BEFORE draining
// ...
const recentStarts = this.store.listRuns({ limit: 1000 })
    .filter(run => Date.parse(run.claimedAt) >= Date.now() - 3_600_000).length;
let capacity = Math.min(
    Math.max(0, policy.maxConcurrentRuns - this.activeRuns.size),
    Math.max(0, policy.maxStartsPerHour - recentStarts));
// per candidate:
if (policyGeneration !== this.automationPolicyGeneration) return;   // checked before approve AND run
```
```ts
private canAutomaticallyApprove(task, policy): boolean {
    const latestIntentActors = [task.createdBy, task.updatedBy];
    if (latestIntentActors.some(a => a.kind === "system" && a.id === "file_reconciler")) return false;
    if (!policy.applyToAgentCreated && latestIntentActors.some(a => a.kind === "agent")) return false;
    return this.taskChainDepth(task) <= policy.maxChainDepth;
}
private taskChainDepth(task): number {   // walk originTaskId chain; cycle ⇒ +∞ ⇒ veto
    let depth = 0; let current = task; const seen = new Set([task.taskId]);
    while (current.originTaskId) {
        if (seen.has(current.originTaskId)) return Number.POSITIVE_INFINITY;
        ...
}
```

**Flow:** queue → microtask pump (re-queued in `finally` if scopes arrived mid-pump, so no busy loop) → per scope: skip `manual` mode → expireTasks → capacity = min(free concurrency slots, hourly-start budget over trailing 1h by `run.claimedAt`) → list candidates (`pending_approval|approved`, `automationEligible`, available now) → per candidate: provenance gate (raw file_reconciler intent NEVER self-approves; agent intent only when `applyToAgentCreated`; chain depth ≤ maxChainDepth with cycle ⇒ ∞) → approve as AUTOMATION_ACTOR → for `auto_start` additionally require `runtime.isInteractiveClientAvailable() === true` → runTask through the SAME admission ladder → per-candidate try/catch logs and continues.
**Invariant:** the generation counter aborts an in-flight pump the instant policy changes — a paused-mid-pump candidate is never claimed after its policy flipped to manual; capacity is recomputed from durable runs, so a crash cannot leak budget.
**Probe:** `agenda-task-manager.test.ts`: "drains saturated automation scopes without a microtask loop" (:704-742) pins maxStartsPerHour=1 yielding exactly one startSession across two workspaces; "does not auto-approve agent-edited or raw-file intent" (:744-786) pins both vetoes leaving everything `pending_approval` with zero startSession calls; "stops claiming candidates when automation is paused mid-pump" (:788-831) parks startSession, flips policy to manual, resolves the first session, and asserts the second task stays pending_approval.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.pumpAutomation" });
await mcp.codebase_memory.get_code_snippet({ project: "cline", qualified_name: "cline.sdk.packages.core.src.tasks.agenda-task-manager.AgendaTaskManager.canAutomaticallyApprove" });
```

## Verdict
Adopt the single-flight latch + generation-counter abort + measured-capacity loop for any auto-scheduler that mutates user-visible state. Adopt the provenance veto: raw imported artifacts must never self-execute. Adapt actor taxonomy and budget windows. Omit the interactive-client gate if every start is headless-safe. Runner caveat recorded honestly (no node_modules).
