<!-- capsule-v2 -->
# loop entry normalization — what must the agent-loop entrypoint default, forward, and restore before any workflow step runs?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** How does `loop()` turn raw agent options into a fully-normalized run (id generation, `_internal` defaults, resume stream-state extraction) such that omitting ONE forwarded field silently degrades the whole run?

## Internal-bag defaulting + suspended-stream-state resurrection
**Path/Symbol:** `packages/core/src/loop/loop.ts` : `loop` (:13-178).
**Signature:** `loop<Tools, OUTPUT>(opts: LoopOptions): DestructurableOutput<MastraModelOutput<OUTPUT>>` — throws `LOOP_MODELS_EMPTY` (MastraError, domain LLM, category USER) on empty models.
**Data Shape:** consumes `_internal: StreamInternal` (now/generateId/currentDate injectors, saveQueueManager, memoryConfig, threadId/resourceId/memory/threadExists, transportRef, background-task fields, drainPendingSignals, initialSignalEchoes, toolPayloadTransform); builds `LoopRun` for `workflowLoopStream`; constructs `MastraModelOutput` with `initialState`.

### Decisive source
```typescript
// runId minting is injectable with a typed reason payload:
runIdToUse = idGenerator?.({ idType: 'run', source: 'agent', entityId: agentId,
                             threadId: _internal?.threadId, resourceId: _internal?.resourceId })
             || crypto.randomUUID();

// The comment that IS the capsule — one omitted forward breaks a whole plane:
// "Forward the tool payload transform policy. Every other consumed field is
// rebuilt here and this bag is what hydrates the run scope, so omitting it
// silently drops the policy for the whole run (the scope slot stays unset
// and readScoped falls back to this same bag)."
toolPayloadTransform: _internal?.toolPayloadTransform,

// Resume finds THE live stream state among snapshot steps:
for (const key in existingSnapshot?.context) {
  const step = existingSnapshot?.context[key];
  if (step && step.status === 'suspended' && step.suspendPayload?.__streamState) {
    initialStreamState = step.suspendPayload?.__streamState;   // first match wins
    break;
  }
}
```

**Flow:** validate models → mint/adopt runId → normalize `internalToUse` (defaults: Date.now / generateId / new Date; copies initialSignalEchoes defensively `[......]`; transportRef defaults `{}`) → stamp startTimestamp via injected clock → wire `rotateResponseMessageId` through messageList → build `workflowLoopProps` sharing ONE processorStates map across iterations → optional `modelSpanTracker.wrapStream` tracing wrapper → construct `MastraModelOutput` (model identity from first model, observability context, requestContext, experimentalTransform) → return destructurable output.
**Invariant:** Every consumed `_internal` field MUST appear in `internalToUse` — the bag is the hydration source for the run scope, so a dropped key silently disables its feature for the entire run (the toolPayloadTransform comment generalizes). Resume stream-state extraction takes the FIRST suspended step carrying `__streamState`. The processorStates map is shared, never copied, across loop iterations and both stream paths.
**Probe:** `packages/core/src/loop/loop.test.ts` (:39+) — AISDK v5 and v6/V3-model describe blocks exercise the entry end-to-end; the field-forwarding invariant itself is comment-documented (see also `tool-payload-transform-forwarding.test.ts` in `packages/core/src/loop/`).
**Coverage caveat:** per-field defaulting has no dedicated unit suite; the forwarding regression test exists only for toolPayloadTransform.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "workflowLoopStream StreamInternal LOOP_MODELS_EMPTY rotateResponseMessageId", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: explicit re-build of every legacy options bag at the entry (with the why-comment attached), injectable id/clock generation, and first-suspended-step state resurrection. Adapt error taxonomy (`MastraError` ids) to your framework. Omit the AI SDK v5/v6 dual-model plumbing if single-vendor. Porters who spread `_internal` blindly instead of rebuilding it forward stale test doubles into production runs; who skip defensive echo-array copying alias caller-owned arrays.
