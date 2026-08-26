<!-- capsule-v2 -->
# Bridge user-message steering — how do steering retries across reconnects stay exactly-once?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** The host blindly re-sends every pending steer request after a reconnect — what must the bridge queue guarantee so the runtime observes each message once but answers every retry?

## Idempotent-by-messageId queue × resend-on-reconnect submitter
**Path/Symbol:** `packages/harness/src/bridge/index.ts` — `createBridgeUserMessageQueue` (:98–215), ownership gate (:751–777); `packages/harness/src/utils/bridge-user-message-submitter.ts` — `experimental_createBridgeUserMessageSubmitter` (:19–96).
**Signature:** `enqueue({messageId, text}): void`; `submit(text): Promise<void>`; `onReconnect(listener): () => void`.
**Data Shape:** `user-message{messageId?, text}` → `user-message-response{messageId, accepted, error?}`; queue entry `{response?, reject}` keyed by messageId.

### Decisive source
```ts
// index.ts:115 — a retried frame replays the STORED response, never re-delivers
const enqueue = (input) => {
  const existing = entries.get(input.messageId);
  if (existing != null) {
    if (existing.response != null) options.respond(existing.response); // dedup answer
    return;                                   // …and never reaches the adapter again
  }
  const settle = (response) => { if (settled) return; settled = true; … }
// index.ts:762 — only the owner may steer
if (ws !== activeSocket) sendControl(ws, {…accepted: false,
  error: { message: 'The connection does not own the active bridge turn.' }});
```
```ts
// bridge-user-message-submitter.ts:47 — the trusting client half
const unsubscribeReconnect = options.onReconnect(() => {
  for (const entry of pending.values()) send(entry.request);   // blind resend
});
```

**Flow:** host `submit()` mints a UUID messageId and registers a pending promise → frames cross the socket (queued in `pendingSends` while disconnected) → on reconnect the channel fires onReconnect and the submitter RE-SENDS all pendings → the bridge either already has an entry (replays stored accept/reject response) or enqueues it fresh for the adapter's async-iterator → adapter calls `accept()`/`reject()` once; late duplicate responses hit the settled latch and no-op.
**Invariant:** Exactly-once DELIVERY is enforced by the server-side id map, not by client caution — the client may always resend; responses are settle-once per messageId; close() rejects every unresolved entry with "ended before accepting" so submitters can't hang; steering requires BOTH an active turn AND stream ownership.
**Probe:** direct tests `packages/harness/src/bridge/index.test.ts:310–345` ("deduplicates retried user messages by messageId" — two responses sent, adapter observed count **1**), :272–308 ("rejects user messages from a connection that does not own the turn"), :347–364 ("no active turn"), :208–248 (pendingCount ladder `[0,1,0]` around accept).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createBridgeUserMessageSubmitter enqueue pendingCount", limit: 5 });
// verified live @9d9a73f — experimental_createBridgeUserMessageSubmitter rank#1 (4 callers); createBridgeUserMessageQueue :98-215
```

## Verdict
Adopt the split responsibility (server dedups by idempotency key, client resends freely) for any human-steering channel over a lossy/reconnecting transport; adapt message ids/response shapes to host wire format; omit the ownership gate only if your transport has exactly one authorized sender. Caveat: none — dedup, ownership, and ack ladders are unit-pinned at this pin.
