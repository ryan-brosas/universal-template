<!-- capsule-v2 -->
# Block-resume reassembly — parallel vs conditional resume completion rules

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** After resuming ONE step inside a parallel or conditional block, how is the block-level result rebuilt?

## Parallel requires ALL; conditional counts only executed arms
**Path/Symbol:** `packages/core/src/workflows/handlers/entry.ts:buildResumedBlockResult` (:38-118); resume-path consumption at :350-393 (parallel) and :415-502+ (conditional, `onlyExecutedSteps: true` at :502).
**Signature:** `buildResumedBlockResult(entrySteps, stepResults, executionContext, opts?: { onlyExecutedSteps?: boolean }): any`.
**Data Shape:** `resume.resumePath` is a MUTABLE array — the block consumes its own index via `resume.resumePath.shift()` before recursing into the child entry.

### Decisive source
```ts
const stepsToCheck = opts?.onlyExecutedSteps
  ? entrySteps.filter(s => isSingleStepEntry(s) && stepResults[getSingleStepEntryId(s)] !== undefined)
  : entrySteps;

const allComplete = stepsToCheck.every(s => { ... return r && r.status === 'success'; });
```

**Flow:** shift resumePath → execute just the targeted branch → rebuild: all-complete ⇒ success with `{stepId: output}` map; any failed ⇒ failed (error + tripwire carried, default error text 'Workflow step failed after resume'); else suspended ⇒ suspended + re-register `suspendedPaths[id] = [...executionPath, stepIndex]` for EVERY still-suspended member.
**Invariant:** Conditional blocks must NOT wait on arms whose conditions selected nothing at original run time — hence `onlyExecutedSteps` filters to arms present in stepResults. Parallel uses full membership. The suspendedPaths re-registration inside the rebuild (not the caller) is what makes a SECOND suspend of a sibling arm resumable.
**Probe:** `grep -c 'onlyExecutedSteps' packages/core/src/workflows/handlers/entry.ts` from repo root (=3) and `grep -c "resumePath.shift()" packages/core/src/workflows/handlers/entry.ts` (=2). Direct tests: `packages/core/src/workflows/nested-suspend-steps.test.ts`, `concurrent-resume.test.ts`, `nested-resume-label.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "buildResumedBlockResult resumePath parallel conditional", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the all-vs-executed split and mutable resumePath shift-consumption. Adapt result shapes to your run schema. Omit requestContext pass-through if your host has none.
