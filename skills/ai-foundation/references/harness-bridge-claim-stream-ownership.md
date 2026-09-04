<!-- capsule-v2 -->
# Harness bridge stream ownership — who receives the events when any number of hosts may hold a socket?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When multiple WebSocket clients connect to one in-sandbox runtime process, how do you stop a control-only client (e.g. one that only sends `abort`) from silently stealing the event stream?

## Claim-on-work ownership inside runBridge
**Path/Symbol:** `packages/harness/src/bridge/index.ts` — `activeSocket` state (:376–383), claim on `start` (:661) and `resume` (:782–786), owner-close no-op (:886–894), `sendControl` reply-to-sender split (:928–944).
**Signature:** `runBridge<TStart extends { type: 'start' }>(options): Promise<BridgeHandle>`; internal `emit(event)` → `activeSocket.send(line)`.
**Data Shape:** one mutable `activeSocket: WebSocket | undefined`; every turn event carries a process-monotonic `seq`; control frames (`user-message-response`, `error`, `bridge-stop`) carry no seq.

### Decisive source
```ts
// index.ts:376 — connecting grants NOTHING; asking for work claims the stream
// The one connection turn events stream to. A socket claims it by asking for
// work — `start` (a turn) or `resume` (a catch-up) — never by connecting:
// every event goes here alone, so claiming on connect would silence a turn
// already streaming to someone else.
let activeSocket: WebSocket | undefined;
...
case 'start': activeSocket = ws; ...
case 'resume':
  activeSocket = ws; // asking for a catch-up claims it too
  // Synchronous, so no event can slip out live ahead of the replayed tail.
  replay(ws, msg.lastSeenEventId);
...
ws.on('close', () => {
  // Only the stream owner's close matters ... Crucially we do NOT abort the
  // in-flight turn: it keeps running and its events accumulate in the log.
  if (activeSocket === ws) activeSocket = undefined;
});
```

**Flow:** client connects → gets `bridge-hello{state,lastSeq}` but zero events → sends `start` (new turn) or `resume{lastSeenEventId}` (catch-up) → becomes `activeSocket` → all `emit`s flow only there → owner drops mid-turn ⇒ `activeSocket = undefined`, turn KEEPS running into the log → replacement socket's `resume` replays the tail synchronously then continues live.
**Invariant:** Ownership transfers only via `start`/`resume`; a socket that never claimed (or was displaced) closes as a no-op; an owner disconnect never aborts the in-flight turn; control frames answer the SENDING socket while events ride the separate stateful path — the two channels must never share a routing decision.
**Probe:** direct tests `packages/harness/src/bridge/index.test.ts:502–537` ("keeps streaming to the running turn when a second client connects to abort it" — regression: `b.seqs()` stays empty while A still receives `aborted`+`finish`), :539–557 ("hands the stream to whichever socket asks for the next turn" — B's start steals it for turn 2), :559–576 (parse-error reply goes to sender B, not owner A).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "handleInbound resume replay activeSocket", limit: 5 });
// verified live @9d9a73f — handleInbound :655-802 rank#1; replay :538-544; runBridge :354-926
```

## Verdict
Adopt claim-on-work ownership + reply-to-sender control path verbatim for any multi-client runtime bridge; adapt the hello/capabilities frame to your protocol; omit the specific `bridge-hello` vocabulary. Caveat: none — behavior pinned by three unit tests plus the e2e reconnect suite.
