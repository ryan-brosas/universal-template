<!-- capsule-v2 -->
# Event-emission gate — emitStepEvents === false must short-circuit BEFORE publish

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** How do control-flow handlers suppress watch events, and why is the gate a wrapper rather than an if at each site?

## One predicate wrapper owns the gate in every handler file
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:publishStepEvent` (:42-48) — identical twin in `handlers/entry.ts:24-30`.
**Signature:** `function publishStepEvent(engine: DefaultExecutionEngine, pubsub: PubSub, ...args: Parameters<PubSub['publish']>): Promise<void>`.
**Data Shape:** all watch events publish on topic `` `workflow.events.v2.${runId}` `` with `{ type:'watch', runId, data: {type: 'workflow-step-start'|'workflow-step-progress'|'workflow-step-result'|'workflow-step-suspended'|'workflow-step-finish', payload} }`; foreach iteration progress carries `{completedCount, totalCount, currentIndex, iterationStatus}`.

### Decisive source
```ts
function publishStepEvent(
  engine: DefaultExecutionEngine,
  pubsub: PubSub,
  ...args: Parameters<PubSub['publish']>
): Promise<void> {
  return engine.options.emitStepEvents === false ? Promise.resolve() : pubsub.publish(...args);
}
```

**Flow:** handlers never call `pubsub.publish` directly for step lifecycle events; they call the local wrapper. Foreach additionally emits per-iteration progress events whose construction (`emitIterationProgress` :1013-1032) is cheap but still gated through the same wrapper.
**Invariant:** The check is STRICT equality against literal `false` (not falsy) — an undefined option means events ON. A porter who gates with `if (!engine.options.emitStepEvents)` flips default-on hosts into silent event loss when the option is merely unset. Duplicating the gate inline at N sites instead of the wrapper is how the drift happens.
**Probe:** `grep -c "emitStepEvents === false" packages/core/src/workflows/handlers/control-flow.ts packages/core/src/workflows/handlers/entry.ts` from repo root (=1 line per file, 2 total).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "publishStepEvent emitStepEvents workflow events v2", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper pattern + strict-`=== false` semantics + typed arg passthrough. Adapt topic naming to your bus. Omit progress-event payloads if you have no live-watch UI.
