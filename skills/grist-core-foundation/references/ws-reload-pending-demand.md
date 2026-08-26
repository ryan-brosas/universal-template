<!-- capsule-v2 -->
# ws-reload-pending-demand — How does the server force a stale client to reset, and why does the demand survive evidence that messages were accounted for?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What makes a reconnecting tab receive `needReload:true`, and when does that demand stick despite a valid lastSeqId?

## reloadPending demand latch
**Path/Symbol:** `app/server/lib/Client.ts:_reloadPending` (:108–111), computed `needReload` in `sendConnectMessage` :372–374, consumed `getMissedMessages` :441.
**Signature:** `const needReload = !newClient && !seamlessReconnect; this._reloadPending = needReload;`
**Data Shape:** boolean; comment: "Set when we have told a client to reload, until one turns up that has. The demand goes out over a connection that has just proved unreliable... nothing else would be left to say it again."

### Decisive source
```ts
// getMissedMessages — first line:
if (this._reloadPending || (lastSeqId === null && this._handoverUnconfirmed)) { return; }
```

**Flow:** non-seamless reconnect (client couldn't recover OR fresh Client object) ⇒ demand set + sent as `needReload:true`, docs closed, missed messages dropped through `collectedThrough` → client that never heard the demand reconnects later even WITH a perfect lastSeqId ⇒ `_reloadPending` still forces the gap ⇒ demand re-sent → tab finally reloads connecting with `newClient=1` ⇒ demand cleared (`newClient` branch resets `_lastReceivedReqId=null`, `_handoverUnconfirmed=false`; needReload false) → subsequent blips resume normally.
**Invariant:** reload demand OUTRANKS sequence accounting: once told to start over, "accounting for messages is no help once the demand has gone unheard" (test case row). The demand is edge-triggered but level-held — held until observed (`newClient=1`), because the unreliable connection that caused it cannot be trusted to have delivered it. Contrast with `_handoverUnconfirmed`, which is cleared BY proof of receipt; `_reloadPending` is cleared only by the page starting over.
**Probe:** `test/server/Comm.ts:645` ("should stop demanding a reload once the client has started over" — blip1 needReload:true, newClient=1 clears, blip3 resumes) + matrix rows "reload demanded but lost" at :913–915.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "getMissedMessages", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt needReload = !(fresh-page OR seamless-resume) with the sticky demand latch. Porters who compute needReload purely from message availability will strand clients that lost the demand itself. Adapt what "reload" means for your app (Grist closes all doc sessions and tells the SPA to reboot).
