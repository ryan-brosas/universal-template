<!-- capsule-v2 -->
# Foreach resume-index routing — which iteration receives the resume payload?

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** When a foreach resumes, how is the resume payload routed to the exact suspended index (and only that one)?

## Two routing regimes: explicit forEachIndex vs derived suspend position
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:executeForeach` (:976-996 + :1209-1217); suspend side writes `foreachIndex` at :1360/:1394.
**Signature:** resume param `{ steps; stepResults; resumePayload; resumePath; forEachIndex?: number }`; `const resumeIndex = prevPayload?.status === 'suspended' ? prevPayload?.suspendPayload?.__workflow_meta?.foreachIndex || 0 : 0`.
**Data Shape:** per-index task `{ item: any, k: number, resumeToUse: typeof resume }` where `resumeToUse` is set ONLY for the routed index.

### Decisive source
```ts
let resumeToUse = undefined;
if (resume?.forEachIndex !== undefined) {
  resumeToUse = resume.forEachIndex === k ? resume : undefined;
} else {
  const isIndexSuspended = prevItemResult?.status === 'suspended' || resumeIndex === k;
  if (isIndexSuspended) {
    resumeToUse = resume;
  }
}
```

**Flow:** on suspend the executor records `foreachIndex` (first suspended index) into `suspendPayload.__workflow_meta` and registers `executionContext.suspendedPaths[stepId]` + merged `resumeLabels` → on re-entry every previously-suspended-but-not-resumed index ALSO gets `resumeToUse` in the legacy regime (`isIndexSuspended`), while the explicit regime routes strictly by equality with `resume.forEachIndex` → a resumed-then-completed index has its resume label deleted (:1097-1100).
**Invariant:** The resume payload must go to exactly ONE iteration when `forEachIndex` is explicit; in the derived regime multiple still-suspended indices may each receive it (they were all mid-flight). `|| 0` means a suspended result missing `foreachIndex` metadata defaults to index 0 — a porter who "fixes" this to null breaks legacy snapshots.
**Probe:** `grep -c '__workflow_meta' packages/core/src/workflows/handlers/control-flow.ts` from repo root (=8). Direct test: `packages/core/src/workflows/foreach-suspend-payload.test.ts` exists at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "forEachIndex resume foreach suspend payload", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both routing regimes and the `|| 0` default. Adapt the snapshot key names. Omit the nested-run-id bookkeeping if your foreach cannot contain workflow invocations.
