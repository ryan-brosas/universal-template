<!-- capsule-v2 -->
# Scheduler error-capture decorator — how do unawaited schedule/unschedule failures get reported without stalling boot?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory `ext-ghost`. **Question:** Since no caller awaits adapter.schedule/unschedule, where do their errors go?

## ErrorCapturingSchedulingAdapter
**Path/Symbol:** `ghost/core/core/server/adapters/scheduling/error-capture.ts:ErrorCapturingSchedulingAdapter` (:44–100; redactToken :27–29; withErrorCapture :101–103).
**Signature:** `withErrorCapture(adapter: SchedulingAdapter): SchedulingAdapter` decorating schedule/unschedule/run/register/rescheduleAll.
**Data Shape:** report = sentry.captureException + logging.error `{event: {name: 'scheduler.<op>.failed'}, err, url: <path-only>, time}`.
### Decisive source
```ts
#capture(run, operation, job) {
  try {
    const result = run();
    if (result) {
      Promise.resolve(result).catch((err) => report(err, operation, job));   // async rejection
    }
  } catch (err) {
    report(err, operation, job);                                            // sync throw
  }
}
function redactToken(url: string): string { return url.split('?')[0]; }
```
**Flow:** index.ts wraps the adapter-manager-resolved instance BEFORE PostScheduling uses it → both sync throws and rejected promises from schedule/unschedule land in report → logged with token REDACTED (job URLs carry a signed admin token valid for hours — only the path is safe to record).
**Invariant:** Report-not-propagate is deliberate: rescheduleAll enqueues one job per scheduled post and awaiting each would stall boot behind adapter rate limiting. The decorator must preserve `rescheduleOnBoot` as a GETTER (delegating, not snapshotting) because boot logic reads it after construction. Token redaction is a security invariant of the log surface, not cosmetic.
**Probe:** `grep -cF "url.split" ghost/core/core/server/adapters/scheduling/error-capture.ts` → expect `1`; `grep -cE "Promise\.resolve\(result\)\.catch" ghost/core/core/server/adapters/scheduling/error-capture.ts` → expect `1`; graph anchor resolves rank-1: `search_graph "withErrorCapture redactToken scheduler"` → `error-capture.ts:withErrorCapture :101-103`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ghost", query: "withErrorCapture redactToken scheduler", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capture-decorator pattern (sync+async arms) and path-only URL logging for any fire-and-forget queue writes. Adapt reporter backends; keep getter delegation for feature flags.
