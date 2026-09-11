<!-- capsule-v2 -->
# Raw-chunk stream tracker — how do you reorder out-of-order tool_call deltas into start/delta/end events?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** When a provider streams tool-call fragments keyed by index (id/name/arguments split across chunks, deltas possibly arriving before the name), what state machine turns them into ordered start/delta/end events without dropping or duplicating bytes?

## Index-keyed tracker with name-gated start + pre-start delta buffer
**Path/Symbol:** `src/core/assistant-message/NativeToolCallParser.ts` (`NativeToolCallParser.processRawChunk` :99-167, `processFinishReason` :170-186, `finalizeRawChunks` :189-208, `clearRawChunkState` :211-214; static state `rawChunkTracker: Map<number, {id, name, hasStarted, deltaBuffer}>` :66-74).
**Signature:** `processRawChunk(chunk: {index: number; id?: string; name?: string; arguments?: string}): ToolCallStreamEvent[]`; `processFinishReason(finishReason: string | null | undefined): ToolCallStreamEvent[]`.
**Data Shape:** Events are `ApiStreamToolCallStartChunk | ApiStreamToolCallDeltaChunk | ApiStreamToolCallEndChunk`. Tracker keyed by the provider's parallel-tool-call **index**, not id — several tool calls interleave in one stream.

### Decisive source
```ts
// Deltas can arrive BEFORE the name: buffer them, flush after start
if (!tracked.hasStarted && tracked.name) {
    events.push({ type: "tool_call_start", id: tracked.id, name: tracked.name })
    tracked.hasStarted = true
    for (const bufferedDelta of tracked.deltaBuffer) {
        events.push({ type: "tool_call_delta", id: tracked.id, delta: bufferedDelta })
    }
    tracked.deltaBuffer = []
}
if (args) {
    if (tracked.hasStarted) events.push({ type: "tool_call_delta", ... })
    else tracked.deltaBuffer.push(args)
}
```
End semantics: `processFinishReason("tool_calls")` emits `tool_call_end` for **every** tracked call (guard: tracker size > 0); `finalizeRawChunks()` emits end **only for calls where `hasStarted`** (nameless stragglers never started, so they have no consumer-side identity) and clears the whole tracker. `clearRawChunkState()` is called when a new API request starts to prevent cross-request leakage.

**Flow:** chunk arrives → init tracker slot on first `id` (name may still be empty) → later `name` updates the slot → once name known, emit start + flush buffered deltas → subsequent argument chunks stream as deltas → provider finish_reason `tool_calls` (or final `finalizeRawChunks`) closes all/started calls.
**Invariant:** Argument bytes are NEVER dropped and NEVER emitted before the start event; ordering within a call is preserved even when the provider sends arguments before the name; state does not survive across requests (explicit clear).
**Probe:** `src/core/assistant-message/__tests__/NativeToolCallParser.spec.ts` (:296+ `processStreamingChunk`, :316+ `finalizeStreamingToolCall` suites pin accumulation/finalize; raw-chunk ordering exercised through the same static state).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "NativeToolCallParser processRawChunk rawChunkTracker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the index-keyed tracker + name-gated start + pre-start buffer trio verbatim — it is the minimal correct handling of fragmented parallel tool calls. Adapt event chunk types to your wire format. Omit nothing: finalize-only-started-ends and request-start clearing are load-bearing (dropping them strands or duplicates calls).
