<!-- capsule-v2 -->
# Sleep/sleepUntil dynamic-duration normalization — clamps and serialization guards

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** How do fixed and dynamically-computed sleep durations get normalized before blocking, and what does a durable host change?

## Duration is clamped at the boundary; dynamic dates may arrive serialized
**Path/Symbol:** `packages/core/src/workflows/handlers/sleep.ts:executeSleep` (:46-145) and `executeSleepUntil` (:173-282).
**Signature:** `executeSleep(engine, params): Promise<void>`; `executeSleepUntil` normalizes `date = dateResult instanceof Date ? dateResult : new Date(dateResult)` after the fn runs inside `wrapDurableOperation`.
**Data Shape:** entry `{ type:'sleep'|'sleepUntil', id, duration?|date?, fn? }`; when `fn` is present the span attribute `sleepType: 'dynamic' | 'fixed'` distinguishes them; duration result updates the span (`durationMs`) AFTER evaluation.

### Decisive source
```ts
await engine.executeSleepDuration(
  !duration || duration < 0 ? 0 : duration,
  entry.id,
  workflowId,
  abortController?.signal,
);
```

**Flow:** create WORKFLOW_SLEEP span → if `fn`, evaluate duration/date inside `wrapDurableOperation` (context includes a deliberately no-op `suspend`: "TODO: this function shouldn't have suspend probably?") → clamp → delegate to engine hook → end span; errors go through `errorChildSpan` then RE-THROW (sleep failure is a real step failure).
**Invariant:** Negative/undefined duration becomes 0 — never an error and never a negative wait. For sleepUntil: missing date after evaluation ends the span with `.nodate` suffix and returns silently (no sleep); past dates yield `Math.max(0, ...)` negative-difference clamps. The re-throw after errorChildSpan is load-bearing: swallowing it would turn every sleep error into a silent success.
**Probe:** `grep -c '!duration || duration < 0 ? 0 : duration' packages/core/src/workflows/handlers/sleep.ts` from repo root (=1). Direct test: `packages/core/src/workflows/cancel-sleep.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "executeSleepDuration executeSleepUntilDate abortableSleep", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the clamp ladder + nodate early-return + re-throw-after-error-span. Adapt the actual waiting primitive via `executeSleepDuration/Date` overrides for your host. Omit ToolStream writer plumbing if you don't stream step output.
