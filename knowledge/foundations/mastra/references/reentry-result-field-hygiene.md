<!-- capsule-v2 -->
# Step-result re-entry hygiene — omitPriorCompletionFields before every re-run

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** What stale fields must be stripped when a step result from a prior attempt is reused as the base for a new attempt?

## Eight completion/suspend fields are destructured away; everything else carries forward
**Path/Symbol:** `packages/core/src/workflows/utils.ts:omitPriorCompletionFields` (:759-777); consumers: foreach stepInfo build (`handlers/control-flow.ts:941`), `onStepExecutionStart` event payload (`default.ts:255`), and the generic strip at :745-756.
**Signature:** `omitPriorCompletionFields<T extends Record<string, unknown>>(stepInfo: T): Omit<T, 'output'|'error'|'endedAt'|'suspendedAt'|'suspendPayload'|'suspendOutput'|'tripwire'|'nonRetryable'>`.
**Data Shape:** rest-destructuring removal — identity fields (id, payload, startedAt, status, metadata) survive.

### Decisive source
```ts
const {
  output: _output,
  error: _error,
  endedAt: _endedAt,
  suspendedAt: _suspendedAt,
  suspendPayload: _suspendPayload,
  suspendOutput: _suspendOutput,
  tripwire: _tripwire,
  nonRetryable: _nonRetryable,
  ...rest
} = stepInfo;
return rest;
```

**Flow:** re-entry (resume/restart/timeTravel/foreach retry) takes the PRIOR result object → strips the eight terminal fields → spreads fresh attempt fields over it (foreach: `...omitPriorCompletionFields(stepResults[stepId] ?? {})` then resume-or-payload + started/resumed timestamps :939-945).
**Invariant:** Without the strip, a resumed run would publish watch events and build stepInfo carrying a previous attempt's `output`/`error`/`endedAt`, which downstream status conversion reads as already-terminal. The exact field SET is the contract — adding a ninth field to StepResult without updating this list reintroduces stale-state bugs.
**Probe:** `grep -c "omitPriorCompletionFields((stepResults\[stepId\] ?? {})" packages/core/src/workflows/handlers/control-flow.ts` from repo root (=1). Companion helper `getResumeLabelsByStepId` (:215-228) scopes persisted label maps by step id — verified live-resolving in graph.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "omitPriorCompletionFields step result strip", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the field list as a named helper called at EVERY re-entry point. Adapt names to your result schema. Omit nothing — partial strips are the bug class this exists to kill.
