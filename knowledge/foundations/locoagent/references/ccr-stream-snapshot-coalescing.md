<!-- capsule-v2 -->
# CCR stream snapshot coalescing — how do you emit text deltas so a client connecting mid-stream sees complete text instead of fragments?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When relaying a token stream over a batched event API where each event may be retried or joined mid-flight, what is the accumulator algebra that makes every emitted delta self-contained?

## Persistent full-so-far accumulator keyed by API message ID
**Path/Symbol:** `src/cli/transports/ccrClient.ts`: `StreamAccumulatorState`/:104-114, `createStreamAccumulator`/:116-118, `scopeKey`/:120-125, `accumulateStreamEvents`/:141-203, `clearStreamAccumulatorForMessage`/:210-223; wiring `writeEvent`/:735-751, `flushStreamEventBuffer`/:771-786.
**Signature:** `accumulateStreamEvents(buffer: SDKPartialAssistantMessage[], state: StreamAccumulatorState): EventPayload[]`; state = `{ byMessage: Map<string /*msg_id*/, string[][] /*blocks→chunks*/>, scopeToMessage: Map<string /*scope*/, string /*msg_id*/> }`.
**Data Shape:** scopeKey = `` `${session_id}:${parent_tool_use_id ?? ''}` `` — content_block_delta events carry NO message id (only message_start does), so a scope→active-message map routes deltas to their message; at most one message streams per scope at a time. The accumulator PERSISTS ACROSS flushes (it is a CCRClient field, not per-flush state).

### Decisive source
```ts
case 'content_block_delta': {
  if (msg.event.delta.type !== 'text_delta') { out.push(msg); break }
  const messageId = state.scopeToMessage.get(scopeKey(msg))
  const blocks = messageId ? state.byMessage.get(messageId) : undefined
  if (!blocks) {
    // Delta without a preceding message_start (reconnect mid-stream,
    // or message_start was in a prior buffer that got dropped). Pass
    // through raw — can't produce a full-so-far snapshot without the
    // prior chunks anyway.
    out.push(msg); break
  }
  const chunks = (blocks[msg.event.index] ??= [])
  chunks.push(msg.event.delta.text)
  const existing = touched.get(chunks)      // Map<string[], CoalescedStreamEvent>
  if (existing) { existing.event.delta.text = chunks.join(''); break }
  ... // new snapshot REUSES msg.uuid — the FIRST text_delta uuid seen for
      // that block in this flush — so server-side idempotency stays stable
}
```
```ts
// Cleanup is driven by the COMPLETE assistant message, not stop events:
if (message.type === 'assistant') {
  clearStreamAccumulatorForMessage(this.streamTextAccumulator, message)
}
// "reliable even when abort/error paths skip content_block_stop/message_stop"
```

**Flow:** writeEvent(stream_event) → delay buffer → 100ms timer → flushStreamEventBuffer swaps out the buffer → accumulateStreamEvents folds text_deltas into snapshots → enqueue as ephemeral client events. message_start records scope→id and deletes any PRIOR id's blocks (a second message_start in one scope supersedes). Non-text-delta events pass through unchanged.
**Invariant:** Each emitted text_delta carries the FULL accumulated text from the start of its block — never a fragment — so a mid-stream subscriber renders correctly from any join point. Snapshot identity (first uuid of the flush) makes retries idempotent server-side. Orphan deltas (no live message_start) degrade to pass-through rather than being dropped. Never clear on stop events; clear on complete-message arrival only. close() clears both maps (:991-992).
**Probe:** `grep -n "full-so-far" src/cli/transports/ccrClient.ts` (`:38,:128,:171,:731,:766`; capital-F variant at `:280`), `grep -n "touched.get(chunks)" src/cli/transports/ccrClient.ts` (`:178`), `grep -n "clearStreamAccumulatorForMessage(this.streamTextAccumulator" src/cli/transports/ccrClient.ts` (`:748`), `grep -n "state.scopeToMessage.delete(scope)" src/cli/transports/ccrClient.ts` (`:221`). No upstream unit tests cover this file — deterministic anchors are the probe tier (recorded caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "accumulate stream events text delta full-so-far snapshot content block", limit: 6 });
// rank#1 → accumulateStreamEvents src/cli/transports/ccrClient.ts :141-203 (executed live pre-write)
```

## Verdict
Adopt whenever you relay an LLM token stream through ANY store-and-forward channel (queues, webhooks, poll APIs). Adapt the key to whatever your delta frames actually carry. Omit the scope map only if your delta frames include the message id natively.
