<!-- capsule-v2 -->
# workflow-run-output stream lifecycle — how do result/usage promises, status transitions, and multi-subscriber fanout survive a stream pipeline that can error instead of close?

**Source:** mastra Apache-2.0 `main@3d2ff0d0a959792331f7cfb12dab6d08506676e7`; Codebase Memory `ext-mastra`. **Question:** When a workflow's event stream is consumed through a promise-facing output object, how do you guarantee every consumer eventually settles — even when `pipeTo` rejects so `close()` never runs?

## Pipe-to-sink state machine with per-subscriber detachable fanout
**Path/Symbol:** `packages/core/src/stream/RunOutput.ts` : `WorkflowRunOutput` (:16-546) — constructor sink (:54-164), `#finalizeWithError` (:224-266), `resume` (:290-389), `fullStream` getter (:408-461), `#updateUsageCount` (:173-214).
**Signature:** `new WorkflowRunOutput({ runId: string; workflowId: string; stream: ReadableStream<WorkflowStreamEvent> })`; getters `status`, `result: Promise<TResult>`, `usage: Promise<LanguageModelUsage>` (each lazily starting consumption via `#getDelayedPromise`).
**Data Shape:** private state = `#status` (`'running'|'success'|'failed'|'suspended'|'paused'|'canceled'|'tripwire'`), `#tripwireData`, `#usageCount` (6-field aggregate incl. `cachedInputTokens`, `cacheCreationInputTokens`, `reasoningTokens`), `#bufferedChunks` (replay log), `#streamFinished`, two `DelayedPromise`s (`usage`, `result`). Chunk grammar consumed: `workflow-start | workflow-step-output | workflow-step-result(status,tripwire?) | workflow-step-suspended | workflow-canceled | workflow-paused | workflow-step-finish (silently dropped from buffer)`.

### Decisive source
```typescript
// The pipeline rejection path — the entire reason #finalizeWithError exists:
// when pipeTo rejects, WritableStream.close() NEVER runs, so without this
// the terminal workflow-finish never fires and every fullStream consumer
// hangs forever.
stream.pipeTo(new WritableStream({ /* start/write/close */ }))
      .catch(reason => { self.#finalizeWithError(reason); });

#finalizeWithError(reason) {
  if (this.#streamFinished) return;          // clean close already finalized
  this.#status = 'failed';                    // overwrite paused/suspended/canceled/tripwire
  // …emit terminal workflow-finish with metadata.error…
  Object.entries(this.#delayedPromises).forEach(([_key, promise]) => {
    if (promise.status.type === 'pending') promise.reject(error);   // no await-forever
  });
  this.#streamFinished = true;
}
```

**Flow:** constructor wires ONE pipeTo sink → `start()` synthesizes + buffers a `workflow-start` → each `write()` updates status (suspended/paused/canceled/failed/tripwire — tripwire detected on `workflow-step-result` with `payload.tripwire`) and accumulates usage from nested `output.payload.usage` (handles both AI SDK v5 `inputTokens/outputTokens` AND v1 `promptTokens/completionTokens`, parseInt-coerced) → `close()` defaults running→success, emits terminal `workflow-finish` carrying usage + optional `finalWorkflowResult` (only on success) + `tripwire` (only on tripwire status), resolves usage, REJECTS any still-pending delayed promises, sets `#streamFinished`.
**Invariant:** (1) Every settlement path — clean close, pipeline error, `rejectResults` — must emit exactly one terminal `workflow-finish` and settle BOTH delayed promises; missing any branch hangs consumers. (2) `fullStream` is an emitter-fanout over shared buffered history: late subscribers replay `#bufferedChunks` first, then live chunks; `cancel()` detaches ONLY its own listeners via a captured `detach` closure — `removeAllListeners()` would kill every concurrent subscriber of the same run (issue #19743). (3) `resume(stream)` resets `#streamFinished/#consumptionStarted/#status='running'` and FRESHES both delayed promises — stale resolvers from the pre-suspend segment must not leak into the resumed run. (4) Deprecation shims (`locked/cancel/getReader/tee/pipeTo…`) all delegate to `fullStream.*` with console warnings — one canonical stream surface.
**Probe:** `packages/core/src/stream/RunOutput.test.ts` (273L): `includes the canonical workflow result in the terminal event` (:83), `cancelling one fullStream consumer does not detach the others` (:150), `rejects result/usage and closes consumers when the stream pipeline errors` (:177), `…after resume()` (:199), `does not stop other fullStream subscribers when one subscriber cancels (#19743)` (:227).
**Coverage caveat:** none — direct vitest suite pins every settlement path at this commit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "WorkflowRunOutput finalizeWithError fullStream", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-settlement-path contract (close / pipe-reject / explicit reject) and the per-subscriber detach pattern for shared EventEmitter fanout. Adapt the chunk-type vocabulary and usage-field unions to your own wire format. Omit the deprecated shim surface unless you also need API-transition compatibility. Porters who forget the `.catch(→finalize)` on `pipeTo` ship a hang-on-error bug that no happy-path test catches.
