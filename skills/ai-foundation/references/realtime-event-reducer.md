<!-- capsule-v2 -->
# Realtime event reducer — how do server events become UIMessage parts without message churn?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does `RealtimeEventReducer` assemble streaming text, tool args, and late transcriptions into a stable UI transcript?

## Accumulator + location-map state machine
**Path/Symbol:** `packages/ai/src/realtime/realtime-event-reducer.ts` — accumulator maps (:62–70), `reduceServerEvent` (:115–250), `getOrCreateAssistantMessage` (:264–291), `appendTextDelta` (:347–386), `addInputTranscriptionMessage` (:293–345), `ensureToolPart` (:409–441), event ring buffer (:252–262).
**Signature:** `reduceServerEvent(state, event): Promise<{state: RealtimeState, effects: RealtimeReducerEffect[]}>`; `maxEvents ?? 500`.
**Data Shape:** per-item maps: `textAccumulators`, `toolArgAccumulators`, `itemIdToPartLocation {messageId, partIndex}`, `toolCallIdToMessageId`, `toolCallIdToName`, `inputAudioMessageInsertIndex`.

### Decisive source
```ts
case 'function-call-arguments-delta': {
  const { state, messageId } = this.getOrCreateAssistantMessage(nextState);
  this.toolCallIdToMessageId.set(event.callId, messageId);
  const acc = this.toolArgAccumulators.get(event.callId) ?? '';
  this.toolArgAccumulators.set(event.callId, acc + event.delta);
  nextState = this.ensureToolPart(nextState, messageId, event.callId);
}
// ensureToolPart seeds the part with EMPTY name:
{ type: 'dynamic-tool', toolName: '', toolCallId: callId,
  state: 'input-streaming', input: undefined }
// delayed transcription insertion:
const insertIndex = Math.min(
  this.inputAudioMessageInsertIndex.get(itemId) ?? state.messages.length,
  state.messages.length);                    // clamped to current end
messages.splice(insertIndex, 0, userTextMessage);
```

**Flow:** text/tool-arg deltas accumulate in maps keyed by itemId/callId; the FIRST delta for an item creates (or reuses — `currentAssistantMessageId`) the assistant message and records its part index; subsequent deltas UPDATE that exact slot in place → `*-done` events finalize from server-provided full text (falling back to accumulated), delete accumulators, and flip part states (`streaming→done`, `input-streaming→input-available` with parsed args; parse failure emits an `error` EFFECT instead of executing with garbage) → `audio-committed` records where the user's utterance WILL sit in the transcript, so a LATE `input-transcription-completed` inserts the user message at the recorded position rather than appending after the model's reply → every raw event is appended to a ring buffer capped at maxEvents.
**Invariant:** Message identity is stable across streaming — parts are updated BY LOCATION MAP, never re-created (a port that appends new parts per delta produces flickering duplicated bubbles). Tool names arrive only at `-done`, so the seeded part carries `toolName: ''` until then. Transcription position bookkeeping exists because transcription and response completion race; unrecorded items fall back to append-at-end.
**Probe:** deterministic: `grep -n "inputAudioMessageInsertIndex.get(itemId) ?? state.messages.length" packages/ai/src/realtime/realtime-event-reducer.ts` → `324:`; `grep -n "toolName: ''" packages/ai/src/realtime/realtime-event-reducer.ts` → `432:`; `grep -n "Failed to parse tool arguments" packages/ai/src/realtime/realtime-event-reducer.ts` → `228:`; `grep -c "currentAssistantMessageId = null" packages/ai/src/realtime/realtime-event-reducer.ts` → `2`. Direct tests: `realtime-event-reducer.test.ts:8` text assembly, `:41` tool-name retention on output, `:93` delayed transcription insertion order.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "addInputTranscriptionMessage insertIndex", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 RealtimeEventReducer.addInputTranscriptionMessage :293-345
```

## Verdict
Adopt the accumulator+location-map design, empty-name seeding, and position-recorded transcription insertion verbatim; adapt event type names to your realtime protocol; omit nothing — identity-churning reducers are the classic wrong port for streaming transcripts.
