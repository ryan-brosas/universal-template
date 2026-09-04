<!-- capsule-v2 -->
# Foreach failure-progress persistence — failed runs must carry `__workflow_meta.foreachOutput`

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** Why do re-run/time-traveled failed foreach steps re-execute already-successful iterations, and what must the failure result carry to prevent it?

## The #21749 fix: persist per-iteration progress on the FAILURE path too
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:executeForeach` (:1303-1318).
**Signature:** failure return `{ ...finalErrorResult, suspendPayload: { ...finalErrorResult.suspendPayload, __workflow_meta: { ...__workflow_meta, foreachOutput: prevForeachOutput, resumeLabels } } }`.
**Data Shape:** `prevForeachOutput: PersistedForeachStepResult[]` — one slot per index; suspended iterations store the full result (suspendPayload preserved for agent `__streamState`), completed ones are stored with `suspendPayload: {}` to keep snapshots small (:1144-1148).

### Decisive source
```ts
// Persist the per-iteration progress accumulated before the failure, using
// the same `__workflow_meta.foreachOutput` channel the suspend path below
// uses. Re-entering this foreach (via time travel, or any other path that
// replays the step) then skips the iterations that already succeeded
// instead of running their side effects a second time. See issue #21749.
return {
  ...finalErrorResult,
  suspendPayload: {
    ...finalErrorResult.suspendPayload,
    __workflow_meta: {
      ...(finalErrorResult.suspendPayload as any)?.__workflow_meta,
      foreachOutput: prevForeachOutput,
      resumeLabels: executionContext.resumeLabels,
    },
  },
} as StepFailure<any, any, any, any>;
```

**Flow:** worker records every iteration outcome into `prevForeachOutput[k]` (including a synthetic `{status:'failed', error, payload:undefined, startedAt, endedAt}` when the iteration THREW outside the normal result channel :1149-1166) → on failure, that array rides out inside `suspendPayload.__workflow_meta` → on re-entry, enqueue loop skips entries with `status==='success'` and restores outputs/`nestedRunId`s from them (:1176-1207).
**Invariant:** A foreach failure result WITHOUT this metadata causes duplicate side effects (publishing/billing/uploads) on recovery — the skip logic keys exclusively on `foreachOutput[k].status === 'success'`. The thrown-in-worker case must ALSO be recorded into `prevForeachOutput[k]`, or the retry reports a hole in progress instead of a failed iteration.
**Probe:** `grep -o 'foreachOutput' packages/core/src/workflows/handlers/control-flow.ts | wc -l` from repo root (=4: read :992 + write :1314 + :1395 + comment). Direct tests: `packages/core/src/workflows/foreach-failure-progress.test.ts` (4 its incl. `'records per-iteration progress on the failed foreach step result'` :114 and `'does not re-run successful iterations when time travelling to the failed foreach'` :103).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "foreachOutput workflow_meta iteration progress", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: persist per-index results on BOTH suspend and failure paths; record thrown errors into the ledger; keep suspended payloads whole while collapsing finished ones. Adapt the metadata key name to your snapshot schema. Omit nothing here — dropping the failure-path half is the exact upstream regression (#21749) documented in-source.
