<!-- capsule-v2 -->
# WS uuid replay dispatch — how do you make request/response over a fire-and-forget socket idempotent under timeouts?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** The transfer client sends a command over WebSocket and waits for a matching response; if the response is lost or slow, the client must retry — but the server may have ALREADY executed the operation. How do you make the retry safe?

## Uuid dedup-replay seam
**Path/Symbol:** client `packages/core/data-transfer/src/strapi/providers/utils.ts:createDispatcher` (33–196), `dispatch` (45–134) with `sendPeriodically` (84–95) and `onResponse` (98–131); server `packages/core/data-transfer/src/strapi/remote/handlers/utils.ts:handlerControllerFactory` (145–394) with `addUUID/hasUUID` (202–208), `respond` (231–277), `executeAndRespond` (296–315); duplicate handling in `packages/core/data-transfer/src/strapi/remote/handlers/push.ts:onMessage` (229–283).
**Signature:** `createDispatcher(ws, retryMessageOptions = {retryMessageMaxRetries: 5, retryMessageTimeout: 30000}, reportInfo?): {dispatch, dispatchCommand, dispatchTransferAction, dispatchTransferStep, setTransferProperties}`; server handler prototype methods `addUUID(uuid)`, `hasUUID(uuid)`, `respond(uuid, e, data)`, `executeAndRespond(uuid, fn)`.
**Data Shape:** every message carries a client-generated `uuid`; response envelope = `{uuid, data: data ?? null, error: e ? {code: e.name ?? 'ERR', message, details} : null}`. Server keeps a per-connection `messageUUIDs: Set<string>` and the last `response` object.

### Decisive source
```ts
// push.ts onMessage — a DUPLICATE uuid does NOT re-execute; it replays the previous response
if (proto.hasUUID(msg.uuid)) {
  const previousResponse = proto.response;
  if (previousResponse?.uuid === msg.uuid) {
    await this.respond(previousResponse?.uuid, previousResponse.e, previousResponse.data);
  }
  return;
}
const { uuid, type } = msg;
proto.addUUID(uuid);
```
```ts
// providers/utils.ts dispatch — resend the SAME payload+uuid on an interval until answered
const sendPeriodically = () => {
  if (numberOfTimesMessageWasSent <= retryMessageMaxRetries) {
    numberOfTimesMessageWasSent += 1;
    ws.send(stringifiedPayload, ...);   // identical bytes, identical uuid
  } else {
    reject(new ProviderError('error', 'Request timed out'));
  }
};
const interval = setInterval(sendPeriodically, retryMessageTimeout);
...
if (response.uuid === uuid) { clearInterval(interval); ... } else { ws.once('message', onResponse); }
```
```ts
// handlers/utils.ts — long transfers disable HTTP timeouts AND db lifecycle hooks for the
// connection lifetime; both restored in the close finally block
disableTimeouts();                 // headersTimeout = requestTimeout = 0
strapi.db.lifecycles.disable();
...
ws.on('close', async (...args) => {
  try { await handler.onClose(...args); } catch (err) { ... cannotRespondHandler(err); }
  finally {
    resetTimeouts();
    strapi.db.lifecycles.enable();
  }
});
```

**Flow:** client `dispatch()` generates one uuid per logical message, sends `{...message, uuid}`, and starts an interval that re-sends the IDENTICAL payload every `retryMessageTimeout` (default 30s) up to `retryMessageMaxRetries` (default 5) → each incoming WS frame is parsed; frames whose uuid does not match re-subscribe `ws.once('message')` (out-of-order responses to other in-flight messages are tolerated) → match clears the interval and resolves with `data ?? null`, or rejects with a typed error classified by `error.details.step` (`transfer` → ProviderTransferError, `validation` → ProviderValidationError, `initialization` → ProviderInitializationError) → server side: `onMessage` first checks `hasUUID`; a known uuid replays the stored previous response verbatim (idempotent retry) and returns WITHOUT executing; unknown uuids are added to the Set then run through `executeAndRespond`, which stores the response on the handler before sending it → if the socket cannot deliver the error response at all, `cannotRespondHandler` terminates the socket instead of hanging.
**Invariant:** the same uuid must NEVER execute twice — dedup happens BEFORE any validation or execution, so even a failed operation's error is replayed identically on retry; the client must resend byte-identical payloads (same uuid) or the server treats it as a new operation; the response is stored on the handler state BEFORE `send` so a mid-send crash still has something to replay; timeout/lifecycle disabling is paired with a `finally` restore on close — a leaked disable would silently break normal request handling after the transfer; non-matching response frames must not be dropped (re-subscribe) or concurrent dispatches deadlock.
**Probe:** no direct unit test for the dispatcher/handler pair exists in the checkout (recorded coverage caveat); the envelope + step-classification contract is exercised indirectly by every remote-destination test harness (`src/strapi/providers/remote-destination/__tests__/*.test.ts` mock `dispatchCommand/dispatchTransferStep` returning the exact `{ok, stats}` / error shapes the server produces), and the upgrade/timeout behavior is pinned by direct read of `handleWSUpgrade` (handlers/utils.ts 119–143).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "hasUUID addUUID executeAndRespond sendPeriodically", file_pattern: "packages/core/data-transfer/src/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 4 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the full pair as one unit: client same-uuid periodic resend + server pre-execution dedup-replay. That combination is the portable answer to "idempotent RPC over an unreliable channel" without sequence numbers or acks. Adopt the store-response-before-send rule and the terminate-instead-of-hang fallback. Adapt the retry ladder defaults (5 × 30s) and the typed-error classification to your error taxonomy. Omit Strapi's HTTP-timeout and lifecycle-hook disabling unless your host also runs other traffic on the same server during long uploads. Coverage caveat: no direct unit test for either half of the protocol in the checkout; wire contract pinned by the remote-destination mock harnesses.
