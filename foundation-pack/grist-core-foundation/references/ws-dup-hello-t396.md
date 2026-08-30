<!-- capsule-v2 -->
# ws-dup-hello-t396 — Why is the clientConnect greeting sent twice, and under what guard does the duplicate go out?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What browser race makes the first hello vanish, and what exact guard re-sends it?

## Dup-hello workaround (T396)
**Path/Symbol:** `app/server/lib/Client.ts:sendConnectMessage` tail (:417–424).
**Signature:** `await delay(250); if (!this._destroyed && this._websocket?.isOpen) { await this._sendToWebsocket(JSON.stringify({ ...clientConnectMsg, dup: true })); }`.
**Data Shape:** identical payload + `dup:true`; sent ONLY if still connected after the delay.

### Decisive source
```ts
// A heavy-handed fix to T396, since 'clientConnect' is sometimes not seen in
// the browser, (seemingly when the 'message' event is triggered before 'open'
// on the native WebSocket.) See also my report at
// https://stackoverflow.com/a/48411315/328565
await delay(250);

if (!this._destroyed && this._websocket?.isOpen) {
  await this._sendToWebsocket(JSON.stringify({ ...clientConnectMsg, dup: true }));
}
```

**Flow:** clientConnect #1 goes out immediately after connect bookkeeping → `await delay(250)` → still alive AND socket open ⇒ hello re-sent with dup:true → browser dedupes (client treats dup as replay of the same seqId-less announcement) → needReload connections never reach this path (socket closed right after the single hello).
**Invariant:** the bug is a native-WebSocket event-ordering race ('message' handler attached before 'open' misses early frames), so the fix must be SERVER-side redundancy with a liveness guard — sending blindly would hit dead sockets; skipping the delay reintroduces the race window. The dup flag exists so client-side logging/telemetry can distinguish replays. Porters who "clean up" the second send strand real users in a state where the tab waits forever for a hello that was eaten.
**Probe:** deterministic source pins only — no direct unit spec (coverage caveat recorded); reconnect tests (:346–733) all depend on hello delivery through the full path including the dup.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "sendConnectMessage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt guarded server-side hello duplication for browser WebSocket compat. Adapt delay to your RTT profile. Keep the dup marker — debugging reconnect storms without it is misery.
