<!-- capsule-v2 -->
# Job envelope economics — why retryLimit: 0 on a fan-out job?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How should a queue job that submits paid API calls be configured for expiry and retries?

## No queue-level retry; expiry outlasts the fan-out
**Path/Symbol:** `apps/worker/src/jobs/process-prompt.ts:PROMPT_JOB_OPTIONS` (L57–60), rationale comment (L41–56); consumer `scheduleNextRun` (L75–96).
**Signature:** `const PROMPT_JOB_OPTIONS = { retryLimit: 0, expireInSeconds: 90 * 60 } as const`.
**Data Shape:** one process-prompt job = one prompt cycle = submit EVERY due target × replication at once; runtime ≈ slowest run (bounded by provider task ceilings), hence 90min > any single fan-out.

### Decisive source
```ts
// If pg-boss expires the job it cannot cancel the running promises, and a
// retry would pay for the fan-out a second time.
// … By the time this job can fail it has already submitted paid requests,
// and a queue-level retry re-submits the whole fan-out including the runs
// that succeeded. Recovery goes through the handler's own backoff reschedule
// instead, or through schedule-maintenance for a job that died before reaching it.
export const PROMPT_JOB_OPTIONS = { retryLimit: 0, expireInSeconds: 90 * 60 } as const;
```

**Flow:** handler ends by scheduling its own successor (`boss.send("process-prompt", {promptId, consecutiveFailures}, {singletonKey: "prompt-"+id, singletonSeconds: startAfterSeconds, startAfter, ...PROMPT_JOB_OPTIONS})`). Reschedule failure is logged and swallowed — failing the job for a scheduling hiccup would kill an otherwise-complete cycle. Deleted prompt → return without rescheduling (chain ends cleanly). Disabled prompt/brand → reschedule anyway so re-enabling works without maintenance.
**Invariant:** recovery from partial failure is the HANDLER's backoff ladder + maintenance sweep, never the queue's retry — a queue retry double-bills successful runs. Singleton key prevents duplicate chains per prompt.
**Probe:** no direct unit test (queue wiring); the cost-contract composition IS tested via scheduling-under-failure.test.ts. State this caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "PROMPT_JOB_OPTIONS scheduleNextRun singletonKey processPromptJob", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the retryLimit-0 + self-rescheduling pattern for any job whose failure mode is "already spent money"; adapt expiry to your slowest legal fan-out; omit the singleton mechanics if your queue dedupes differently.
