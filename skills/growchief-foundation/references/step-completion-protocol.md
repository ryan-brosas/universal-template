<!-- capsule-v2 -->
# Step-completion protocol — how do sequential campaign steps execute through a SHARED per-bot queue without a distributed lock?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** N campaign workflows share one account's throttler queue; how does each campaign keep its steps ordered and learn when its step actually ran?

## enqueue + stepCompleted handshake over workflow signals
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.bot.jobs.ts:workflowBotJobs` (:29-147); answering side `workflow.throttle.ts` (:369-390); signal defs `signals/step.completed.signal.ts`, `signals/cancel.all.signal.ts`.
**Signature:** producer: `throttler.signal(enqueue, {...Work, stepId})` then `await condition(() => completedSteps.has(stepId))`; consumer: after final success `signal(stepCompleted, job.stepId)` on the ORIGIN workflow handle (`getExternalWorkflowHandle(job.workflowInternalId)`).
**Data Shape:** `completedSteps = new Set<string>()` lives inside the bot-jobs workflow; throttler→origin signaling carries only the stepId string.

### Decisive source
```ts
// producer (workflowBotJobs), per step in declared order:
await workingHoursManager.ensureWithinWorkingHours();
// 'delay' pseudo-tool sleeps inline (minus time already spent waiting on hours):
if (step.data.identifier === 'delay') {
  const adjustedDelayMs = Math.max(0, step.data.settings.hours * 3600_000 - workingHoursWaitTime);
  if (adjustedDelayMs > 0) await sleep(adjustedDelayMs);
} else {
  await throttler.signal(enqueue, { ..., priority: tool.priority, totalRepeat: 0 });
  await condition(() => completedSteps.has(stepId)); // blocks THIS campaign only
}
// consumer (throttler) — only when the job is DONE for good:
if (!repeatJob && job.leadId !== 'ignore' && !job.ignoreLead) { await saveActivity(...); }
if (!repeatJob) {
  try { await getExternalWorkflowHandle(job.workflowInternalId).signal(stepCompleted, job.stepId); }
  catch (error) {}
}
```

**Flow:** campaign starts/ensures the per-bot throttler child (deterministic id `user-throttler-${botId}`, `parentClosePolicy: ABANDON` so the immortal gate outlives campaigns) → registers `cancelAll` handler that cancels a local `CancellationScope` → for each step: wait hours, enqueue, block until the throttler echoes completion → finally `saveActivity('completed')`.
**Invariant:** `stepCompleted` fires ONLY on the non-repeat path — a `repeatJob:true` outcome (retry later) does NOT advance the campaign, so ordering survives retries; every completion echo is wrapped in try/catch because the origin workflow may already be cancelled/dead, and that must not kill the throttler loop.
**Probe:** no test runner upstream. Deterministic pins: `grep -n "completedSteps.has(stepId)" apps/orchestrator/src/workflows/workflow.bot.jobs.ts` → :139; `grep -n 'signal(stepCompleted' apps/orchestrator/src/workflows/workflow.throttle.ts` → :385-388; ABANDON wiring :55-58.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "stepCompleted enqueue cancelAll", limit: 10 });
```

## Verdict
Adopt: shared-gate pattern where per-campaign order is enforced by blocking on an ack signal rather than locking the queue itself. Adapt signal names/runtime. Omit the delay-step special case if your DSL has no pseudo-tools.
