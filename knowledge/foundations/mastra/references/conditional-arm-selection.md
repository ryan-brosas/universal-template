<!-- capsule-v2 -->
# Conditional arm selection — what happens when a condition throws, and how are unselected time-travel arms reconciled?

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** How does the conditional block evaluate N conditions concurrently and what must a porter replicate so failed conditions don't kill the run?

## All conditions evaluate; a throwing condition selects nothing instead of failing the block
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:executeConditional` (:305-598).
**Signature:** `executeConditional(engine, params): Promise<StepResult>` with `entry: { type: 'conditional'; steps: SingleStepEntry[]; conditions: ConditionFunction[] }`.
**Data Shape:** `truthyIndexes = (await Promise.all(entry.conditions.map(async (cond, index) => ...))).filter(index => index !== null)` — each condition runs through `engine.evaluateCondition(cond, index, context, operationId)` which returns `index` when truthy or `null` when falsy.

### Decisive source
```ts
} catch (e: unknown) {
  const errorInstance = getErrorFromUnknown(e, { serializeStack: false });
  const mastraError = new MastraError(
    { id: 'WORKFLOW_CONDITION_EVALUATION_FAILED',
      domain: ErrorDomain.MASTRA_WORKFLOW,
      category: ErrorCategory.USER,
      details: { workflowId, runId } },
    errorInstance,
  );
  engine.getLogger()?.trackException(mastraError);
  ...
  return null;   // condition failure == "not selected", NOT a run failure
}
```

**Flow:** eval every condition in parallel (each wrapped in its own WORKFLOW_CONDITIONAL_EVAL span) → filter nulls → select arms whose indexes survived → perStep/timeTravel narrows to first runnable → reconcile stale 'running' markings → execute selected arms via Promise.all.
**Invariant:** A throwing condition is logged-and-treated-as-false — it never rejects the Promise.all nor fails the workflow. Separately, under time travel an arm pre-marked 'running' by reconstructed stepResults but NOT selected by its re-evaluated condition must be rewritten to `{status:'skipped', payload, startedAt, endedAt}` (:473-486) or a rehydrated run renders the wrong branch as active. Both behaviors are load-bearing; porting only one is the classic wrong-port.
**Probe:** `grep -c 'WORKFLOW_CONDITION_EVALUATION_FAILED' packages/core/src/workflows/handlers/control-flow.ts` from repo root (=1, inside the catch). Direct test: `packages/core/src/workflows/timetravel-divergence.test.ts:127` pins `'branch-b'` status `'skipped'` for the unselected conditional sibling.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "executeConditional conditional truthyIndexes", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: throw-to-false condition semantics + skipped-reconcile for time-traveled unselected arms + resume-path bypass that skips condition re-evaluation on resume (`handlers/entry.ts:415+`). Adapt the MastraError taxonomy to your error domain. Omit the deprecation-proxy context construction (`runCount` shim) if your host never had that param.
