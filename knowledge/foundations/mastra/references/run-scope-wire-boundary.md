<!-- capsule-v2 -->
# run-scope serialization boundary — where do non-JSON-safe runtime handles live when workflow steps cross a stringify wire?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** When an agent loop runs as evented workflow steps whose inputs/outputs pass through `JSON.stringify` (storage snapshots, Unix-socket frames), how do live class instances, closures, and abort controllers survive — and what is the migration contract for legacy `_internal` bags?

## Typed per-run scope + hydrate-once/read-fallback/write-mirror accessors
**Path/Symbol:** `packages/core/src/mastra/run-scope.ts` : `RunScopeKey/createRunScope/MapRunScope` (:1-91); `packages/core/src/loop/run-scope-keys.ts` : 22 typed keys (`NOW_KEY`, `SAVE_QUEUE_MANAGER_KEY`, `STEP_TOOLS_KEY`, `TRANSPORT_REF_KEY`, …); `packages/core/src/loop/run-scope-access.ts` : `getRunScope` (:30), `readScoped` (:41), `writeScoped` (:60); `packages/core/src/loop/hydrate-run-scope.ts` : `hydrateRunScopeFromInternal` (:35-66); lifecycle on `packages/core/src/mastra/index.ts` : `__registerInternalWorkflow` (:3384-3408), `__unregisterInternalWorkflow` (:3416-3424), `__createRunScope/__releaseRunScope` (:3437-3470), `#sweepStaleRunScopedWorkflows` (:3601-3622).
**Signature:**
```typescript
createRunScopeKey<T>(label: string): RunScopeKey<T>;        // fresh Symbol per call; phantom __t type
readScoped<T>(ctx: { mastra?; runId?; _internal? }, key: RunScopeKey<T>, internalField: keyof StreamInternal): T | undefined;
writeScoped<T>(ctx, key, internalField, value): void;       // writes scope AND mirrors to _internal
hydrateRunScopeFromInternal(mastra: Mastra, runId: string, internal?: StreamInternal): void;
```
**Data Shape:** scope = `Map<symbol, unknown>` keyed by branded symbols, held per-`runId` on the Mastra instance with a refcount (`#runScopeRefcounts`) so parent + nested sub-agent workflows sharing a runId keep the scope alive until the LAST unregister. Nothing in the scope is ever persisted or published.

### Decisive source
```typescript
// The dual-bag read/write contract that keeps legacy tests working:
export function readScoped<T>(ctx, key, internalField): T | undefined {
  const scope = getRunScope(ctx);
  if (scope) { const v = scope.get(key); if (v !== undefined) return v; }
  return ctx._internal?.[internalField] as T | undefined;    // test-only fallback
}
// And the hydration exclusion rule — runtime OUTPUTS are NOT hydrated:
// "Intentionally NOT hydrated here: stepTools, stepActiveTools, stepWorkspace,
// _delegationBailed. Those are *runtime-written outputs* of step execution,
// not bootstrap inputs — hydrating them would seed the scope with stale/empty
// values." Pre-populated bootstrap inputs (durable resume via resolveInternalState)
// still work because readScoped falls back to _internal[field].
```

**Flow:** `loop()` normalizes `_internal` defaults (now/generateId/transportRef…; forwards `toolPayloadTransform` explicitly or the policy silently drops for the whole run — comment-pinned) → `workflowLoopStream` calls `hydrateRunScopeFromInternal` AFTER `__registerInternalWorkflow` allocated the scope (so refcount untouched) → step factories read via `readScoped`, write via `writeScoped` (mirror preserves "caller reads `_internal` after" legacy contract).
**Invariant:** Step input/output schemas must stay JSON-safe — enforced by `serialization-invariants.test.ts` which walks zod schemas for forbidden handle keys and asserts the codec never tags Class/Function envelopes. Scope lifecycle = refcounted alloc/release PLUS TTL sweep of idle registrations (activity timestamps keyed `${workflow.id}:${runId}`); the sweep releases by STORED runId, never by parsing the composite key ("callers can pass runIds that contain ':'"). Run-scoped registrations never overwrite the bare `${id}` slot.
**Probe:** `packages/core/src/loop/workflows/serialization-invariants.test.ts`: `llmIterationOutputSchema does not include forbidden handle keys` (:91), `SaveQueueManager / BackgroundTaskManager / Memory / TransportRef live on runScope` (:114), `STEP_TOOLS keeps live execute closures by reference` (:133), `DRAIN_PENDING_SIGNALS holds a function, which would be lost via JSON` (:144), `encoding a representative iteration output never tags a Class or Function envelope` (:156). Also `packages/core/src/mastra/run-scope.test.ts`.
**Coverage caveat:** none at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "readScoped writeScoped hydrateRunScopeFromInternal __registerInternalWorkflow", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: typed-symbol scope slots next to their consumers; hydrate-bootstrap-inputs-only rule; write-mirror for legacy observers; refcount + stored-runId TTL sweep. Adapt the key registry to your domain types. Omit the Phase-2 codec references. A porter who hydrates runtime-written slots seeds stale values overwritten only by accident; who parses runId out of `${id}:${runId}` breaks on ids containing colons — both traps are comment-documented upstream because they were real bugs.
