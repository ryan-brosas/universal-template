<!-- capsule-v2 -->
# ws-inflight-request-voucher — On reconnect, which in-flight client requests should be resent, which awaited, and which rejected?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** A request was mid-flight when the socket died — how does the client decide resend-vs-wait-vs-reject without repeating work or stranding callers?

## lastReceivedReqId voucher protocol
**Path/Symbol:** `app/server/lib/Client.ts:_lastReceivedReqId` (:113–115), recorded `_onMessageImpl` :500–502, volunteered in `sendConnectMessage` :396, reset on newClient :362–368; client twin `app/client/components/Comm.ts:_resendPendingRequest` (exercised by tests).
**Signature:** `lastReceivedReqId: seamlessReconnect ? (this._lastReceivedReqId ?? "none") : undefined` in CommClientConnect.
**Data Shape:** server tracks highest reqId READ off the socket (requests arrive in order); "none" = connected but read zero requests; `undefined` = field absent = server is not offering a resume, says nothing.

### Decisive source
```ts
// Only meaningful when resuming the session; otherwise no earlier request survives.
lastReceivedReqId: seamlessReconnect ? (this._lastReceivedReqId ?? "none") : undefined,
```
Client decision table (test/server/Comm.ts:986–1010, 13 pinned rows):
- never sent ⇒ RESEND (no effect yet; always safe)
- sent ∧ lastReceivedReqId ≥ reqId ⇒ WAIT ("it is in hand, and the answer cannot go astray")
- sent ∧ lastReceivedReqId < reqId (∞ counts) ⇒ RESEND ("provably never arrived")
- sent ∧ field undefined, OR needReload, OR request went on another connection ⇒ REJECT "interrupted by reconnect"
- stale boundClientId only bites rows where the request would otherwise be held back (RESEND→reject; WAIT unaffected)

**Flow:** every request carries reqId; server stamps `_lastReceivedReqId` BEFORE executing → only a SEAMLESS resume volunteers the voucher → client compares each pending request's reqId against it: covered ⇒ wait for the answer the server owes; provably-unarrived ⇒ resend; unverifiable ⇒ reject with "interrupted by reconnect" (repeating possibly-applied work is worse than failing a request that never landed).
**Invariant:** three-way outcome is exhaustive and mutually exclusive; the distinction undefined-vs-"none" is semantic (silent ≠ read-nothing) and porters who collapse them will either resend applied work or strand resumable requests. Reset discipline: a reloaded tab numbers requests from zero, so `newClient=1` MUST null `_lastReceivedReqId` or the server would vouch for request #42 of a page at #0 (test :666).
**Probe:** `test/server/Comm.ts:482` ("should reject a request the server cannot vouch for" — destroyAllClients then reconnect ⇒ rejected /interrupted by reconnect/), :499 ("should ask again for a request that never reached the server"), matrix :975–1072.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_onMessageImpl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reqId voucher + three-way classification verbatim — it is the subtlest correctness seam in the plane. Adapt error strings. Omit GristWSConnection transport details; the protocol lives at the message-semantics layer.
