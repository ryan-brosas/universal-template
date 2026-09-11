<!-- capsule-v2 -->
# Engine hook surface — the override lattice that makes one engine durable across hosts

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** Which DefaultExecutionEngine methods are designed to be overridden for platform-specific durability, and what are the default behaviors a porter must reproduce?

## Every side effect funnels through an overridable hook with an inert default
**Path/Symbol:** `packages/core/src/workflows/default.ts:DefaultExecutionEngine` (:158-354 + :700-735).
**Signature:** hooks: `executeSleepDuration(duration, sleepId, workflowId, abortSignal)` / `executeSleepUntilDate(date, ...)` / `wrapDurableOperation<T>(operationId, operationFn)` / `getEngineContext()` / `evaluateCondition(conditionFn, index, context, operationId): Promise<number|null>` / `onStepExecutionStart(params): Promise<number>` / `executeWorkflowStep(params): Promise<StepResult|null>` / `createStepSpan`/`endStepSpan`/`errorStepSpan`/`createChildSpan` + `requiresDurableContextSerialization()` / `buildMutableContext` / `applyMutableContext`.
**Data Shape:** `evaluateCondition` returns the INDEX when truthy and `null` when falsy (not a boolean) — control-flow filters `.filter(index => index !== null)`. `executeWorkflowStep` returning `null` means "use standard execution" (Inngest returns a real result).

### Decisive source
```ts
async wrapDurableOperation<T>(_operationId: string, operationFn: () => Promise<T>): Promise<T> {
  return operationFn();
}
...
async evaluateCondition(...): Promise<number | null> {
  return this.wrapDurableOperation(operationId, async () => {
    const result = await conditionFn(context);
    return result ? index : null;
  });
}
```

**Flow:** dynamic sleep fns, condition evaluation, step-start timestamps, nested-workflow invocation and ALL span lifecycle calls route through these hooks; the Inngest subclass (`workflows/inngest/src/execution-engine.ts:57 extends DefaultExecutionEngine`) overrides them so replays memoize instead of re-executing. Mutable context (`state`, `suspendedPaths`, `resumeLabels`) is built before a child runs and Object.assign-applied after (:731-735).
**Invariant:** The default engine is deliberately NON-durable (pass-by-reference requestContext `requiresDurableContextSerialization(): false`; `wrapDurableOperation` = plain await). A porter embedding this in a replay-based host must override the hooks as a SET — overriding only `executeSleepDuration` while leaving `wrapDurableOperation` inert gives half-durable semantics where sleeps survive but condition evaluations don't.
**Probe:** `grep -c 'wrapDurableOperation' packages/core/src/workflows/default.ts` from repo root (=4). Direct tests: `packages/core/src/workflows/durable-operation-ids.test.ts`, `default.test.ts` (13 describes) exist at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "DefaultExecutionEngine wrapDurableOperation evaluateCondition hooks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the hook taxonomy + index-or-null condition contract + mutable-context round-trip. Adapt per host durability model (this is THE extension seam of the repo). Omit span-hook durability if you have no tracing.
