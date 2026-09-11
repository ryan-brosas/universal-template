<!-- capsule-v2 -->
# Continuation run-id wire rule — when must a follow-up run NOT pin the originating runId on the wire?

**Source:** copilotkit MIT `main@e9387e04835545c45744b791aee7c9c03520be31`; Codebase Memory `ext-copilotkit`. **Question:** A human-in-the-loop tool resolved and the recursive follow-up run is issued — should it reuse the original run's id on the transport, and what breaks if it does?

## Logical-run identity vs. wire run-id split in runAgent
**Path/Symbol:** `packages/core/src/core/run-handler.ts:RunHandler.runAgent` (:424-573; decision at :497-538, comment block :515-527).
**Signature:** `async runAgent({ agent, forwardedProps?, resume?, runId? }: CopilotKitCoreRunAgentParams, continuationHandoff?: CopilotKitCoreContinuationHandoff): Promise<RunAgentResult>`
**Data Shape:** `logicalRunId` (local) starts as caller `runId`; overwritten from `params.input.runId` inside a wrapped `onRunStartedEvent` ONLY for ordinary runs. `continuationHandoff` present ⇒ internal continuation.

### Decisive source
```typescript
agentSubscriber.onRunStartedEvent = async (params) => {
  started = true;
  // A continuation keeps reporting under the run it continues; only an
  // ordinary run adopts the id the transport assigned it.
  if (!continuationHandoff) {
    logicalRunId = params.input.runId;
  }
  return onRunStartedEvent?.(params);
};
// ...
// An internal continuation ... deliberately does NOT pin the originating run
// id on the wire. Pinning it made the transport treat the follow-up as a
// resumption of a run it had already completed: it re-delivered that
// run's applied half — duplicating every tool call already on the
// message, each duplicate carrying empty arguments — and the follow-up's
// own tool call never reached client state, so its card never rendered.
const pinRunIdOnWire = runId !== undefined && !continuationHandoff;
const agentRunInput = {
  forwardedProps: { ...this._internal.properties, ...forwardedProps },
  ...(resume !== undefined ? { resume } : {}),
  ...(pinRunIdOnWire ? { runId } : {}),
  tools: this.buildFrontendTools(agent.agentId),
  context: this._internal.getContextForAgent(agent.agentId),
};
```

**Flow:** caller passes `runId` → subscriber wraps `onRunStartedEvent` to capture the transport-assigned id (ordinary runs adopt it; continuations keep the caller's logical id) → `pinRunIdOnWire` is true ONLY for an explicit `runId` WITHOUT a continuation handoff → the follow-up runs as a NEW invocation on the wire while the state manager (`markNextRunAsContinuation`) re-stamps its events onto the logical `runId`, so downstream tracing still sees one run.
**Invariant:** One logical run downstream ≠ one wire run: external callers may pin `runId`; internal continuations must never carry it, or the transport replays the completed run's applied half (duplicate empty-argument tool calls, lost final card).
**Probe:** `packages/runtime/src/v2/runtime/runner/__tests__/intelligence-runner.test.ts` covers runner-side continuation handling; core-side deterministic anchor: `grep -n "pinRunIdOnWire" packages/core/src/core/run-handler.ts` (:528 definition, :535 use).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-copilotkit", query: "runAgent continuationHandoff markNextRunAsContinuation pinRunIdOnWire", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split: logical run identity lives in state management, wire identity belongs to each transport invocation. Adapt handoff plumbing to host state-manager shape. Omit the historical deadlock note only if your AG-UI client ≥0.0.42 (finalize-always-runs guarantee, :445-450).
