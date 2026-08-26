<!-- capsule-v2 -->
# ws-json-memory-pool-backpressure — How does the server admit large JSON responses across all clients without OOM, and why is the reservation corrected mid-flight?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** Before stringifying a response that may be tens of MB, how is memory reserved, corrected to true size, and released?

## Global MemoryPool admission for JSON responses
**Path/Symbol:** `jsonMemoryPool = new MemoryPool(jsonResponseTotalReservation)` (`app/server/lib/Client.ts:35–39`, total 500MB); used ONLY in `Client.sendMessage` :264–310; MemoryPool API at `app/server/lib/MemoryPool.ts` (`withReserved` :64–71).
**Signature:** `await jsonMemoryPool.withReserved(Deps.jsonResponseReservation /* 20MB */, async (updateReservation) => { ... })`.
**Data Shape:** size unknown before JSON.stringify ⇒ flat 20MB estimate reserved first; ~500MB/20MB caps simultaneously-STARTABLE large responses at ~25 ("Together with the above, it works to limit parallelism").

### Decisive source
```ts
await jsonMemoryPool.withReserved(Deps.jsonResponseReservation, async (updateReservation) => {
  if (this._destroyed) {
    // If this Client got destroyed while waiting, stop here and release the reservation.
    return;
  }
  const seqId = this._nextSeqId++;
  const message: string = JSON.stringify({ ...messageObj, seqId });
  const size = Buffer.byteLength(message, "utf8");
  updateReservation(size);
```

**Flow:** reserve flat 20MB → wait until global space frees (backpressure BEFORE any allocation; full socket buffers make websocket.send block, which stalls the pool) → destroyed-while-waiting recheck AFTER acquire (releases reservation of dead clients) → serialize → correct reservation to TRUE utf8 byte length via updateReservation → send → release on completion. On websocket-send failure the message moves into _missedMessages WITHOUT releasing the reservation — documented wrong-but-deliberate (:296–303): holding reservations while disconnected risks freezing future responses, judged MORE dangerous than the temporary over-accounting.
**Invariant:** every response crosses ONE global admission gate; estimate-then-correct prevents small responses from permanently over-reserving; post-acquire destroyed check is load-bearing because waiters wake after their Client died. Slow-client pool exhaustion risk documented, mitigation (destroy slow readers) deliberately not implemented.
**Probe:** coverage caveat: NO dedicated unit spec exercises jsonMemoryPool directly (deterministic source pins only); behavior pinned indirectly by `test/server/Comm.ts:720` ("should receive all server messages (large) in order when send doesn't fail").
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "withReserved", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flat-estimate-then-correct admission control for large serialized responses. Adapt the 500MB/20MB numbers to host capacity. Omit Grist's queued-message-doesn't-release tradeoff unless your disconnect buffer is likewise bounded elsewhere.
