<!-- capsule-v2 -->
# ws-handover-unconfirmed-latch — When the server hands buffered messages to a reconnecting client, how does it avoid losing them if delivery silently fails?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** After giving a client its missed messages, when may the server let go of them, and what state proves the client took ownership?

## handoverUnconfirmed latch
**Path/Symbol:** `app/server/lib/Client.ts:_handoverUnconfirmed` (:104–106 declaration), set :405–408, cleared :354 & :367, consulted `getMissedMessages` :441.
**Signature:** field latch consulted by `getMissedMessages(lastSeqId)`; set/cleared inside `sendConnectMessage`.
**Data Shape:** boolean + the rule: "Set when we have handed a client messages and let go of them. If it comes back saying it received nothing, they are gone. Cleared once it comes back able to account for them."

### Decisive source
```ts
// in sendConnectMessage, AFTER the clientConnect send succeeded:
this._dropMissedMessages(collectedThrough);
if (missedMessages?.length) {
  // A successful send is not proof of arrival, so we are owed an account of these.
  this._handoverUnconfirmed = true;
}
// ...and on seamless resume:
if (missedMessages) { seamlessReconnect = true; this._handoverUnconfirmed = false; }
```

**Flow:** queue messages while away → reconnect presents lastSeqId → full run available ⇒ hand over array, drop from ledger, latch SET (send success ≠ arrival) → client's NEXT reconnect presents `lastSeqId` ≥ handed seqIds ⇒ accounts for them ⇒ latch CLEARED, resume normal → if instead the tab reports nothing (`lastSeqId === null`) while latched, `getMissedMessages` reports a GAP ⇒ needReload (the messages are gone; only a reload recovers).
**Invariant:** the server lets go of buffered data ONLY against a claim of receipt, but a successful websocket send is merely probable delivery — hence the latch keeps ONE bit of doubt alive until the client proves receipt by sequence accounting. Ordering matters: drop-then-latch happens only after `_sendToWebsocket` resolves; a throw skips both (messages stay held, test :605). Clearing happens ONLY via (a) proof-of-receipt resume or (b) `newClient=1` page restart — never on timeout.
**Probe:** `test/server/Comm.ts:619` ("should let a client carry on once it has taken its missed messages" — third blip with NO lastSeqId still resumes: confirmed handover stops being held against the client).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "sendConnectMessage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-state handover protocol (hold → hand-over+latch → prove-or-gap). This is the exact seam that makes "quiet reconnect" safe: silence after a CONFIRMED handover is not suspicion. Adapt message framing; omit Grist's specific swallow/failSend test rig mechanics.
