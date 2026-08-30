<!-- capsule-v2 -->
# ws-connect-choreography — What is the exact ordered handshake for binding a websocket to a Client, and why is each step where it is?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** From raw websocket to streaming messages — what order of authenticate → reuse-decide → bind → announce makes reconnects safe?

## Connection choreography (Comm._onWebSocketConnection + Client.sendConnectMessage)
**Path/Symbol:** `app/server/lib/Comm.ts:_onWebSocketConnection` (:200–259) + `app/server/lib/Client.ts:sendConnectMessage` (:335–430).
**Signature:** `private async _onWebSocketConnection(websocket: GristServerSocket, req: http.IncomingMessage)`; `sendConnectMessage(newClient: boolean, reuseClient: boolean, lastSeqId: number|null, parts: Partial<CommClientConnect>)`.
**Data Shape:** URL params: `clientId`, `browserSettings` (JSON), `newClient` (default "1"; omitted reads as NEW "for the sake of tests"), `lastSeqId`, `counter` (identifies the GristWSConnection instance in the tab), `user` selector.

### Decisive source
```ts
// Comm._onWebSocketConnection, ordered:
// 1. parse params          2. resolveIdentity(req,...) -> AuthSession
// 3. disabledAt check      -> throw ApiError("User is disabled", 403)
// 4. reuse gate            -> reuse or new Client
// 5. client.setConnection({...})            // bind handlers AFTER decision
// 6. client.sendConnectMessage(newClient, reuseClient, lastSeqId, {...})
// wrapper: catch { log.error(...); websocket.terminate(); }  // close() inadequate via LB
```
Inside sendConnectMessage: clear pending `_destroyTimer` FIRST → decide seamless (needs !newClient && reuse && `_isAuthorized()`: every open docFD authorizer.assertAccess("viewers") passes, :546–555) → collect missedMessages → `collectedThrough = _nextSeqId` snapshot → non-seamless: drop-through + closeAllDocs → send `clientConnect` RAW (NOT sendMessage — never queue the hello) → on success drop ≤collectedThrough + arm handover latch → if needReload close socket immediately → else `await delay(250)` and re-send `{...msg, dup:true}` if still open (T396 fix: native WebSocket 'message' before 'open' eats the first clientConnect).

**Flow:** see decisive block — the order IS the invariant list: identity resolved before any Client mutation; disabled users rejected before reuse decision; destroy timer cancelled before any await that could race it; docs closed only when the client truly cannot resume; dup hello sent only while connection still open.
**Invariant:** the connect announcement bypasses the missed-message machinery entirely (`Don't use sendMessage here`) — a queued hello could sit behind messages the client hasn't asked for yet. Authorization re-check on resume (`_isAuthorized`) closes the revoke-during-disconnect window: access lost while away ⇒ docs closed + needReload, never silent continued access. Failure anywhere in the wrapper terminates the RAW socket (load-balancer-safe), it does not queue.
**Probe:** `test/server/Comm.ts:1172` ("should terminate connection for disabled user"), :605 ("keep hold of missed messages if clientConnect cannot be sent" — throw path leaves ledger intact), :686 backoff test (accept-then-terminate forces client exponential backoff ≤6 tries / 8s).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_onWebSocketConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt step order + raw-hello + authorize-on-resume + dup-hello workaround. The 250ms dup and T396 rationale are load-bearing browser-compat armor. Adapt delay/params; omit EIO specifics (see ws-terminate-not-close capsule).
