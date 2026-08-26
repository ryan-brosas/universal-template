<!-- capsule-v2 -->
# Realtime tool gating — when does a voice session request the follow-up response after tool calls?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** How does the session ensure exactly ONE `response-create` fires only after EVERY tool output of a turn is submitted?

## Response-closed + all-submitted conjunction
**Path/Symbol:** `packages/ai/src/realtime/realtime-session.ts` — `toolCallsInResponse`/`submittedToolOutputs`/`responseToolCallsClosed` (:54–56), `addToolOutput` (:193–213), `maybeRequestToolResponse` (:221–233), `response-done` latch (:333–339), `executeToolCall` undefined-contract (:290–322).
**Signature:** `addToolOutput(callId: string, result: unknown): void`; `private maybeRequestToolResponse(): void`.
**Data Shape:** three fields form the gate: Set of calls seen in the response, Set of outputs submitted, boolean "response finished delivering calls".

### Decisive source
```ts
private maybeRequestToolResponse(): void {
  if (!this.responseToolCallsClosed) return;          // response still streaming
  if (this.toolCallsInResponse.size === 0) return;
  for (const callId of this.toolCallsInResponse) {
    if (!this.submittedToolOutputs.has(callId)) return; // ANY missing ⇒ wait
  }
  this.sendEvent({ type: 'response-create' });        // exactly once per turn
  this.toolCallsInResponse.clear();
  this.submittedToolOutputs.clear();
  this.responseToolCallsClosed = false;
}
// handleServerEvent:
if (event.type === 'response-done' && this.toolCallsInResponse.size > 0) {
  this.responseToolCallsClosed = true;
  this.maybeRequestToolResponse();                    // may fire NOW if all in
}
```

**Flow:** each `function-call-arguments-done` adds its callId to the tracking set and executes the handler → handler results auto-submit via `addToolOutput` (send `conversation-item-create` function-call-output, mark submitted, re-check the gate) → `response-done` closes the call window → the FIRST moment both conditions hold (window closed AND every call has an output) fires ONE `response-create` and resets all three fields.
**Invariant:** Per-output triggering is a documented anti-pattern: requesting a response after EACH output lets the model continue without the full multi-tool context (in-source comment :215–220). Returning `undefined` from `onToolCall` is the documented human-in-the-loop escape hatch (:309–314): nothing auto-submits; the app must call `addToolOutput` later or the follow-up response never fires (by design). Handler throws surface via `onError` WITHOUT submitting an output.
**Probe:** deterministic: `grep -n "responseToolCallsClosed = true" packages/ai/src/realtime/realtime-session.ts` → `337:`; `grep -c maybeRequestToolResponse packages/ai/src/realtime/realtime-session.ts` → `3`; `grep -n "documented human-in-the-loop pattern" packages/ai/src/realtime/realtime-session.ts` → `309:`. Direct tests: `realtime-session.test.ts:113` single response after ALL outputs, `:139` no response before done, `:81` undefined = manual flow.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "maybeRequestToolResponse submittedToolOutputs", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 AbstractRealtimeSession.maybeRequestToolResponse :221-233
```

## Verdict
Adopt the two-condition conjunction and reset-on-fire semantics verbatim; adapt event names to your protocol; omit nothing — eager per-output responses are the exact bug this gate exists to prevent.
