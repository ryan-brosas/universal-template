<!-- capsule-v2 -->
# Progress-response vocabulary — what does the single job-outcome triple {delay, repeatJob, endWorkflow} mean at every return site?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** every layer (provider tool → BotManager race → throttler loop) speaks one tiny dialect — what is the complete grammar?

## One discriminated triple governs queue, retry, and lifecycle
**Path/Symbol:** `shared/server/temporal/progress.response.ts` (`ProgressResponse`); consumers: `workflow.throttle.ts` (:279-367), `bot.manager.ts` return ladder (:701-774), `bots.interface.ts:BotAbstract.accountLimited/leadList/screenShare`.
**Signature:** `type ProgressResponse = { delay: number; repeatJob: boolean; endWorkflow: boolean; leads?: ...; restriction?: { type: RestrictionType; message: string } }`.
**Data Shape:** `delay` = ms to sleep before next dispatch; `repeatJob` = re-enqueue this job (totalRepeat+1); `endWorkflow` = signal cancelAll to the origin campaign workflow.

### Decisive source
```ts
// throttler consumption of the vocabulary:
const { endWorkflow, delay, repeatJob, restriction, leads } =
  progressValue || { endWorkflow: true, delay: 0, repeatJob: false, leads: [] }; // null ⇒ fail
...
if (endWorkflow || (repeatJob && job.totalRepeat >= 3))
  await getExternalWorkflowHandle(job.workflowInternalId).signal(cancelAll);   // die
if (repeatJob && job.totalRepeat < 3)
  q.push({ ...job, totalRepeat: job.totalRepeat + 1, date: Date.now() });      // retry
if (delay) await sleep(delay);
```
Return sites and their meanings:
- provider action success → `{delay:0, repeatJob:false, endWorkflow:false}` (continue campaign);
- connectionRequest with `degree===1 || pending` → `{..., endWorkflow:true}` (nothing to do);
- sendMessage duplicate (>0.95 similarity) → `{..., endWorkflow:false}` (already done ≠ failure);
- automation throw w/ live page → `{delay:20000, repeatJob:true}` (transient); closed page → login?false:endWorkflow-true;
- logout / PAUSED-or-not-logged-in → `{repeatJob:true}` (wait for re-login);
- proxy dead → `{delay:1_800_000, repeatJob:true}` WITHOUT state save;
- stuck >240s → watcher resolves `{repeatJob:true}`; outer deadline → thrown 'Retry job after timeout'.

**Flow:** provider returns triple → BotManager post-race ladder may override into sentinels ('logout'/'proxy'/ui-error/false) → throttler applies cancel/requeue/sleep in that fixed order.
**Invariant:** the retry cap lives ONLY in the throttler (`totalRepeat >= 3`) — providers never count their own retries; `leads.length > 0` spawns child campaign workflows BEFORE the outcome triple is applied (leadList jobs are producers, not steps).
**Probe:** no test runner upstream. Deterministic pin: `grep -c 'repeatJob' apps/orchestrator/src/workflows/workflow.throttle.ts` ≥ 5 (:280/:344/:349/:351/:358/:365); cap check :344/:349.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "ProgressResponse endWorkflow repeatJob", limit: 10 });
```

## Verdict
Adopt: one three-field outcome record as the sole inter-layer contract, with the retry counter owned by the scheduler, not the worker. Adapt field names/semantics. Omit nothing — this is pure interface design.
