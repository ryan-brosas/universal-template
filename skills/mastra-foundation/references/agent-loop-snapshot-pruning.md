<!-- capsule-v2 -->
# agent-loop snapshot pruning — which fields of an internal agent-workflow snapshot can be dropped without breaking resume?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** When persisting agent-loop workflow snapshots at every step boundary, which heavy fields are dead weight versus load-bearing resume state, and what is the exact per-status strip matrix?

## Status-matrix pruner over serialized step results
**Path/Symbol:** `packages/core/src/loop/workflows/prune-snapshot.ts` : `pruneAgentLoopSnapshot` (:284-311) with helpers `pruneStepResult` (:192-238), `stripHeavyIterationFields` (:70-94), `stripTerminalOutputFields` (:105-142), `stripStepResultRequest` (:157-162), `stripTerminalPayloadState` (:183-189), `stripStreamState` (:243-257), `pruneResultMirror` (:265-276).
**Signature:** `pruneAgentLoopSnapshot({ snapshot }: { snapshot: WorkflowRunState }): WorkflowRunState`.
**Data Shape:** `WorkflowRunState.context` = map of stepId → serialized step result `{ status, payload, output?, prevOutput?, suspendPayload?, suspendOutput?, resumePayload? }`. Terminal statuses: `'success'|'failed'|'skipped'|'bailed'|'canceled'` (`TERMINAL_STEP_STATUSES`, :43). Heavy fields: `messages`, any `__`-prefixed key, `output.steps[]`, `metadata.request/response`, `stepResult.request`, terminal-payload iteration trio `messageListState/accumulatedSteps/lastStepResult`.

### Decisive source
```typescript
// pruneStepResult: order matters — request-echo strip runs FIRST so it also
// hits non-terminal steps; suspendPayload survives ONLY on non-terminal steps.
pruned.payload = stripStepResultRequest(pruned.payload);
if ('output' in pruned) pruned.output = stripStepResultRequest(pruned.output);
pruned.payload = stripHeavyIterationFields(pruned.payload);
if ('prevOutput' in pruned) pruned.prevOutput = stripHeavyIterationFields(pruned.prevOutput);

if (TERMINAL_STEP_STATUSES.has(result.status)) {
  delete pruned.suspendPayload;   // completed steps are never resumed again
  delete pruned.suspendOutput;
  delete pruned.resumePayload;
  pruned.payload = stripTerminalPayloadState(pruned.payload);
  if ('output' in pruned) pruned.output = stripTerminalOutputFields(pruned.output);
  return pruned;
}
// Non-terminal: suspendPayload kept INTACT (it IS the resume state:
// __streamState, __agentId, tool approvals, __workflow_meta nested-run ids),
// except foreach entries which get per-entry pruning recursively.
```

**Flow:** context.input → `stripHeavyIterationFields` with `__workflowKind` restored afterward (:294-299, the durable-agent recoverability marker must survive its own strip); every other context entry → `pruneStepResult`; `snapshot.result` → `pruneResultMirror` (status mirror of suspended step: keeps routing fields but strips `__streamState` copies, including array-shaped foreach entries :268-274); engine routing state (`suspendedPaths/waitingPaths/activePaths/resumeLabels/serializedStepGraph/status/runId/timestamps/requestContext`) never touched.
**Invariant:** Copy-on-write — never mutates the input snapshot (every helper spreads before deleting). The ONE live `__streamState` copy allowed per suspended run is the suspended step's own `suspendPayload.__streamState`. Terminal steps keep `output.steps` entries but each entry loses `request.body` — the evented engine re-reads step number/stopWhen/processor history from those entries as `inputData` on same-run sibling resume, while the body (tool schemas + system prompt, re-serialized every step) has zero readers. Measured: `stepResult.request` alone was 86.7 MB of 360.7 MB persisted across 300 production snapshots (24%).
**Probe:** `packages/core/src/loop/workflows/prune-snapshot.test.ts` (349L): `strips the request echo from a terminal step on both payload and output` (:50), `keeps a suspended step payload and its resume state intact` (:263), `leaves a terminal output untouched, since a same-run continuation reads it` (:282), `strips completed foreach entries while preserving still-suspended ones` (:306), copy-on-write checks (:203, :329), `drops the threaded iteration state from a terminal payload while keeping routing fields` (:229). Deep-scan helper `countRequestEchoes` proves zero echoes anywhere in mixed snapshots.
**Coverage caveat:** registered ONLY on internal agent workflows (agentic-loop/agentic-execution/durable/network); user-authored workflows keep full history — the file header states this contract explicitly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "pruneAgentLoopSnapshot", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the status-matrix strip (terminal ⇒ drop suspension triple + payload iteration trio + body-of-steps; non-terminal ⇒ keep suspendPayload verbatim) and the restore-after-strip pattern for markers like `__workflowKind`. Adapt field names to your own snapshot schema — the *matrix* is the portable idea, not the key list. Omit the MongoDB-specific 16 MB motivation. A porter who strips `output.steps` wholesale from terminal steps breaks same-run resume; who keeps `suspendPayload` on terminal steps leaks unbounded growth per suspension.
