<!-- capsule-v2 -->
# Client-event dispatch pipeline — where must replay dedup sit so side effects run exactly once in an event-sourced socket stream?

**Source:** OpenHands / All-Hands-AI (MIT) `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** In one WS message handler that both projects events into a store AND fires non-idempotent side effects, what is the correct ordering of buffering, dedup-check, store-write, and effect dispatch?

## Ordered handler: intercept → flush → dedup-check → add → gate → effects
**Path/Symbol:** `src/contexts/conversation-websocket-context.tsx` main message pipeline (:540–758; client-action dispatch sites :724–740; planning mirror :788–792).
**Signature:** `const handleMainMessage = useCallback((messageEvent: MessageEvent) => { … }, [addEvent, consumeMatchingPendingMessage, queryClient, conversationId, …])`.
**Data Shape:** Parsed event discriminated by type guards (`isStreamingDeltaEvent`, `isAgentServerEvent`, `isCanvasUIActionEvent`, `isLaunchChildConversationActionEvent`, `isSwitchLLMObservationEvent`, …). Duplicate probe: `useEventStore.getState().eventIds.has(event.id ?? "")`.

### Decisive source
```ts
// Buffer deltas; nothing else in this handler applies to them.
if (isStreamingDeltaEvent(event)) {
  mainDeltaBatcherRef.current?.enqueue(event);
  return;
}
// Flush buffered deltas before this event so it can't overtake them.
mainDeltaBatcherRef.current?.flush();

// A reconnect replays the backlog from a stale anchor. The store
// dedups by id, but the side-effects below aren't idempotent, so skip
// them for replayed events (#1656).
const isDuplicateEvent = useEventStore
  .getState()
  .eventIds.has(event.id ?? "");
const switchLLMObservation = isSwitchLLMObservationEvent(event)
  ? event
  : null;
addEvent(event);
if (isDuplicateEvent) {
  return;
}
```
```ts
// Handle canvas_ui ActionEvents from both the legacy Python tool and
// the client-defined JSON tool. The server acknowledges immediately;
// the actual UI change happens here on the client.
if (isCanvasUIActionEvent(event)) {
  handleCanvasUIAction(event.action, conversationId ?? null);
}
if (conversationId && isLaunchChildConversationActionEvent(event)) {
  void handleLaunchChildConversationAction(
    event.action, conversationId, event.tool_call_id,
  );
}
```

**Flow:** parse → delta? enqueue+return : flush batcher → read `eventIds` BEFORE `addEvent` → `addEvent` → duplicate? early-return (ALL effects skipped) → guard-routed effects: error banner + telemetry, switchLLM metadata/cache/invalidation, client-tool actions.
**Invariant:** The dedup snapshot must be taken before the store write and the effect section gated on it — the store's own id-dedup does NOT protect side effects because they are not idempotent under reconnect replay (#1656). Deltas never reach this logic (they are transient); every durable event flushes pending deltas first so streamed text cannot be overtaken by its own final event.
**Probe:** `__tests__/contexts/conversation-websocket-context.test.tsx:396-534` — replays bash action+observation and error events through `wsCapture.mainOnMessage` and asserts terminal I/O is not re-appended and a dismissed banner does not re-raise; `:792/:833` pin delta reconciliation and per-conversation buffer discard.

### Secondary invariants worth porting
- Client-tool split at the dispatch site: synchronous UI commands (`canvas_ui`) execute inline; network-performing tools (`launch_child_conversation`) are fired `void` with their own result-reporting protocol (see capsule `client-tool-roundtrip-protocol` — that ledger is a separate concern; this capsule owns only the ordered dispatch).
- The planning sub-conversation socket mirrors the same order with its own batcher/received-counters — copy the ORDER, instantiate per socket.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", query: "conversation websocket provider event handler replay dedup", limit: 10 });
```

## Verdict
Adopt the five-step ordering as a pure state machine around any store with an id Set. Adapt guards/store to your stack (the pass-1 event-store capsule supplies the store half). Omit OpenHands' specific event vocabulary. Coverage caveat: none recorded at pin for the cited ranges.
