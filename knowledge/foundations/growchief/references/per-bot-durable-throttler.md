<!-- capsule-v2 -->
# Per-bot durable throttler — how does one long-lived workflow serialize ALL actions for a single social account without dropping queued work across restarts?

**Source:** growchief AGPL-3.0 `main@abb1e37a`; Codebase Memory `growchief`. **Question:** how do you build a per-account action gate that survives process death, enforces an inter-action gap, and accepts work from many producers?

## Signal-driven queue inside one immortal workflow
**Path/Symbol:** `apps/orchestrator/src/workflows/workflow.throttle.ts:userWorkflowThrottler` (:101-404).
**Signature:** `async function userWorkflowThrottler(opts?: { nextAllowedAt?: number; logged?: boolean; active?: boolean; q?: Work[] })`.
**Data Shape:** workflow-local state: `q: Work[]` (jobs), `currentNextAllowedAt: number` (durable gap deadline), `logged`/`active` flags mutated by signals. `Work` carries workflowInternalId, stepId, nodeId, functionName, leadId, botId, priority, totalRepeat. Producers are OTHER workflows signaling `enqueue` (`defineSignal<[Work]>('enqueue')`, enqueue.signal.ts).

### Decisive source
```ts
const GAP_MS = await getGap();            // activity: per-platform daily-gap setting
let currentNextAllowedAt = nextAllowedAt; // carried across continueAsNew
const lock = new Mutex();
setHandler(enqueue, async (w) => {
  await lock.runExclusive(async () => { q.push(w); q.sort(sortFunction(q)); });
});
while (true) {
  await condition(() => q.length > 0);    // durable wait — no polling
  const job = { ...q[0] };                // snapshot copy; head job
```

**Flow:** signal pushes + re-sorts under mutex → loop wakes → fetch bot details (`getBot`; missing bot ⇒ drop head + `signal(cancelAll)` to its origin workflow) → check per-(bot,functionName) restriction ledger → enforce working hours → sleep until `currentNextAllowedAt` → `condition(() => active && logged)` → run the job as an activity (`progress`) with `PROGRESS_DEADLINE = 10*60*1000` and heartbeatTimeout 30s → set `currentNextAllowedAt = Date.now() + GAP_MS` → splice head, handle repeat/end/delay.
**Invariant:** every queue mutation (push/splice/re-sort) happens under ONE `Mutex().runExclusive` so concurrent signal deliveries cannot interleave mid-restructure; the gap is enforced BEFORE dispatch but set AFTER completion, so a failed/aborted run still pays the gap only once on success timing (`now < currentNextAllowedAt ⇒ await sleep(diff)` — deterministic `Date.now()` in workflows).
**Probe:** no upstream tests exist at this pin (zero *.spec/*.test files). Deterministic pin: `grep -n 'await condition(() => q.length > 0)' apps/orchestrator/src/workflows/workflow.throttle.ts` → :179; mutex wraps :141-146/:148-161/:163-176/:189-191/:339-341/:358-361.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "growchief", query: "userWorkflowThrottler", limit: 5, fields: ["signature", "lines"] });
```

## Verdict
Adopt the pattern: one durable singleton-per-resource workflow owning a signal-fed, mutex-guarded priority queue with a carried-over rate-limit timestamp. Adapt Temporal specifics (setHandler/signal/condition) to your durable-execution runtime. Omit the LinkedIn/X product semantics of `Work.payload`. Coverage caveat: behavior pinned by whole-file source reads, no test runner upstream.
