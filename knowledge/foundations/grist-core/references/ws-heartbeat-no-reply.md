<!-- capsule-v2 -->
# ws-heartbeat-no-reply — Which inbound messages bypass request/response entirely, and what identity does the server log for them?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** How are keepalive beats handled so they neither consume reqIds nor generate error responses, and what is logged?

## beat short-circuit
**Path/Symbol:** `_onMessageImpl` head (`app/server/lib/Client.ts:489–499`).
**Signature:** `if (request.beat) { log.rawInfo("heartbeat", {...getLogMeta(), url: request.url, docId: request.docId}); return; }`.
**Data Shape:** `{beat: true, url?, docId?}` — no reqId needed; docId comes FROM THE CLIENT and is trusted for logging only.

### Decisive source
```ts
if (request.beat) {
  // this is a heart beat, to keep the websocket alive.  No need to reply.
  log.rawInfo("heartbeat", {
    ...this.getLogMeta(),
    url: request.url,
    docId: request.docId,  // caution: trusting client for docId for this purpose.
  });
  return;
}
```

**Flow:** every inbound message hits _onMessageImpl → beat ⇒ log + return BEFORE method dispatch (no reqId echo obligation) → everything else must carry a numeric reqId to update _lastReceivedReqId and receive a response.
**Invariant:** heartbeats deliberately skip the voucher protocol — recording their absence as a "request" would corrupt _lastReceivedReqId comparisons; skipping the reply halves keepalive traffic. The client-supplied docId in logs is flagged untrusted-in-principle ("caution") yet acceptable because it feeds observability, not authorization. Porters who route beats through method dispatch get spurious unknown-method errors and voucher drift.
**Probe:** deterministic source pins only — no dedicated heartbeat spec in test/server/Comm.ts (coverage caveat recorded); keepalive behavior observable via rawInfo "heartbeat" log lines.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "_onMessageImpl", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a pre-dispatch control-message short-circuit that neither consumes sequence/reqId space nor produces responses. Adapt field names; keep the log-but-don't-trust posture for client-supplied identifiers.
