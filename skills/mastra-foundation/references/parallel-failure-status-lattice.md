<!-- capsule-v2 -->
# Parallel block failure-status lattice — which branch's result does a parallel block report?

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** When parallel branches end mixed (one failed, one suspended), which single StepResult does the block return and what fields survive?

## Parallel branches fan out over Promise.all but reduce to ONE status by fixed precedence
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:executeParallel` (:101-273).
**Signature:** `executeParallel(engine: DefaultExecutionEngine, params: ExecuteParallelParams): Promise<StepResult<any, any, any, any>>`.
**Data Shape:** `entry.steps: SingleStepEntry[]` fanned out via `Promise.all(steps.map(...))`; each child runs through `executeChildEntry` dispatch (step|agent|tool|mapping) with its own executionPath `[...executionContext.executionPath, i]`; results land in the shared `stepResults` record keyed by step id via `Object.assign(stepResults, stepExecResult.stepResults)`.

### Decisive source
```ts
const hasFailed = results.find(result => result.status === 'failed') as StepFailure<any, any, any, any>;

const hasSuspended = results.find(result => result.status === 'suspended');
if (hasFailed) {
  // Preserve tripwire property for proper status conversion in fmtReturnValue
  execResults = {
    status: 'failed',
    error: hasFailed.error,
    tripwire: (hasFailed as any).tripwire,
  };
} else if (hasSuspended) {
  execResults = { status: 'suspended', suspendPayload: hasSuspended.suspendPayload, ... };
} else if (abortController?.signal?.aborted) {
  execResults = { status: 'canceled' };
} else { /* success: output = { stepId: output } only for success-status results */ }
```

**Flow:** mark running → `Promise.all` children → reduce: failed > suspended > canceled > success → emit span end/error → return block-level result.
**Invariant:** Status precedence is failed-then-suspended-then-canceled; a block with one failed and one suspended branch reports FAILED (suspension is silently swallowed until retry/re-entry). The `tripwire` field is copied from the failing branch explicitly because `fmtReturnValue` converts tripwire failures differently — dropping it changes run status conversion downstream.
**Probe:** `grep -c 'tripwire: (hasFailed as any).tripwire' packages/core/src/workflows/handlers/control-flow.ts` from repo root (=2: parallel :235 + conditional :559 — both block types preserve it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "executeParallel control-flow parallel branches", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the precedence lattice (failed > suspended > canceled > success) and explicit tripwire propagation — order-independent and portable to any fork/join executor. Adapt the span lifecycle calls (`createChildSpan`/`endChildSpan`) to your tracing stack; omit mastra's watch-event publishing (`workflow.events.v2.*`) which is transport-specific. Direct tests: `packages/core/src/workflows/parallel-nested-restart.test.ts`, `branch-map-bug.test.ts` exist at pin; runner not executed in this clone (no node_modules).
