<!-- capsule-v2 -->
# ws-terminate-not-close — Why does every abnormal websocket teardown use terminate(), and when must listeners be stripped first?

**Source:** GristLabs grist-core Apache-2.0 `main@b83224bbe9c8`; Codebase Memory `grist-core`. **Question:** What is the difference between close() and terminate() here, and which teardown paths use which?

## terminate-vs-close discipline
**Path/Symbol:** comment at three sites: `Comm._createSocketServer` catch :271, `Client.interruptConnection` :222, plus listener-stripping in `interruptConnection` :216–221 and `_onClose` :592.
**Signature:** `websocket.terminate(); // close() is inadequate when ws routed via loadbalancer`.
**Data Shape:** close() = graceful handshake (may be swallowed by LB/proxy); terminate() = immediate TCP-level destruction.

### Decisive source
```ts
} catch (e) {
  log.error("Comm connection for %s threw exception: %s", req.url, e.message);
  websocket.terminate();  // close() is inadequate when ws routed via loadbalancer
}
```

**Flow:** two abnormal-teardown shapes: (a) Comm-level connect failure ⇒ log + terminate RAW socket immediately; (b) Client.interruptConnection ⇒ removeAllListeners THEN re-arm ONLY an onerror logger ("It is important to keep an onerror handler, since otherwise errors bring down the server") THEN terminate THEN null the ref. Graceful path: needReload sends use `.close()` (:413) — deliberate, the connection should end but not violently.
**Invariant:** terminate-not-close for abnormal teardown because graceful close frames can be dropped by load balancers, leaving half-open sockets that block reconnect binding. Strip listeners before terminate to prevent _onMessage/_onClose from running during destruction — BUT keep exactly one onerror sink or Node emits an unhandled 'error' event that crashes the process.
**Probe:** `test/server/Comm.ts:1163` ("should terminate connection on invalid API key"), :1172 ("disabled user" terminates), :686 backoff test depends on accept-then-TERMINATE semantics.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core", query: "interruptConnection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt terminate-for-abnormal / close-for-polite + strip-but-keep-one-error-handler. This is process-survival armor porters routinely omit until their server crashes on a dying socket. Adapt handler names to your transport layer.
