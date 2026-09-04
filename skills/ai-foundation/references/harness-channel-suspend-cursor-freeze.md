<!-- capsule-v2 -->
# SandboxChannel suspend — how does a host process exit mid-turn WITHOUT losing or duplicating the tail?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A workflow slice must hand an in-flight runtime turn to the NEXT process at an exact event boundary — what makes the returned cursor trustworthy?

## Freeze-then-drain suspension with a 'suspended' close reason
**Path/Symbol:** `packages/harness/src/utils/sandbox-channel.ts` — `suspend()` (:302–327), suspended frame drop in `wire` (:349–356), `suspended`/`pinnedSuspensionCursor` state (:157–166), dispatch-chain queueing (:435–437).
**Signature:** `suspend(): Promise<number>` (resolves the hand-off cursor).
**Data Shape:** close reason string `'suspended'` vs `'closed'` vs `'reconnect failed'`; cursor = pinned checkpoint eventId ?? `_lastSeenEventId`.

### Decisive source
```ts
// sandbox-channel.ts:302
async suspend() { return new Promise<number>(resolve => {
  const pinnedSuspensionCursor = this.pinnedSuspensionCursor?.eventId;
  if (this.terminal) { resolve(pinnedSuspensionCursor ?? this._lastSeenEventId); return; }
  // Stop counting/dispatching further inbound frames immediately …
  this.suspended = true;
  this.closing = true;                       // suppresses reconnect too
  this.onClose(() => resolve(pinnedSuspensionCursor ?? this._lastSeenEventId));
  // Queue the close behind any already-dispatched frames so everything
  // delivered to the consumer is reflected in the final cursor.
  this.enqueue(() => { try { this.ws?.close(); } catch {}
                       this.finalizeClose(1000, 'suspended'); });
});}
// wire(): ws.on('message', raw => {
//   if (this.suspended) return;   ← cursor freezes EXACTLY at last delivered event
```

**Flow:** suspend sets `suspended` FIRST so subsequent inbound frames are dropped pre-parse (cursor cannot outrun delivery) → queues socket close behind the dispatch chain → resolves via onClose with reason `'suspended'` → bridge keeps running the turn and accumulates events past the cursor → next process constructs a channel with `initialLastSeenEventId: cursor` and calls `open({ resume: true })`.
**Invariant:** The cursor returned is exactly "everything handed to consumer listeners", never "everything seen on the wire"; suspend is one-way (no resume frame is sent on the dying socket); adapters distinguish slice-boundary from unexpected drop by the `'suspended'` reason and only then resolve `done` successfully; frames after suspend never advance `lastSeenEventId`.
**Probe:** direct tests `packages/harness/src/utils/sandbox-channel.test.ts:118–153` ("suspend freezes the cursor… closes with reason 'suspended'" — post-suspend seq-3 frame changes neither `text` nor cursor; `sent` stays empty), :165–190 (pinned variant resolves **1** while wire-seen cursor is 3); e2e `packages/harness/src/bridge/reconnect.integration.test.ts:124–193` (slice 1 suspends at cursor 2, slice 2 receives exactly `['three','four']`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "SandboxChannel suspend suspended finalizeClose", limit: 5 });
// verified live @9d9a73f — SandboxChannel.suspend :302-327 rank#1; finalizeClose :520-525
```

## Verdict
Adopt drop-inbound-first + queue-close-behind-dispatch + explicit close-reason vocabulary for any resumable stream consumer; adapt reason strings to host error taxonomy; omit pinned-checkpoint resolution if you have no boundary-event concept (see harness-channel-event-checkpoint-pin.md). Caveat: none — unit + e2e pinned.
