<!-- capsule-v2 -->
# SSE subscription router — how do you stream per-connection change events with ack-first framing, capability-narrowed filters, and a graceful-close signal?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should a server hold open subscriptions, deliver only opted-in change types, and tell the client "stream ended on purpose" versus a transport drop?

## Connected graph-selected seam
**Path/Symbol:** `packages/server/src/server/listenRouter.ts`: `createListenRouter` (:122-270), capacity guard + ack-first frame (:140-160), graceful-close teardown (:200-230), `parseListenFilter` (:87-92); filter math in `serverEventBus.ts`: `listenFilterAccepts` (:127-146), `honoredSubset` (:162-177), `InMemoryServerEventBus` publish loop (:66-94).
**Signature:** `serve(message: JSONRPCRequest, signal: AbortSignal|undefined, capabilities: ServerCapabilities, serverInfo: Implementation): Response`; `closeAll(): void`.
**Data Shape:** Subscription id = the listen request's JSON-RPC id VERBATIM (spec-carried; demux is per-connection since each listen has its own SSE stream, so client-chosen ids cannot route across requests). Ack = first SSE frame carrying the HONORED subset (requested ∩ advertised capabilities — honoring without narrowing would fail open and deliver unadvertised types).

### Decisive source
```ts
// Server-side graceful close: emit the empty `subscriptions/listen` JSON-RPC
// result BEFORE closing the stream so the client distinguishes graceful end
// from a transport drop. Written before `closed = true` so writeFrame still enqueues.
writeFrame(`event: message\ndata: ${JSON.stringify({ jsonrpc:'2.0', id: subscriptionId,
    result: { resultType:'complete', _meta:{ [SUBSCRIPTION_ID_META_KEY]: subscriptionId, [SERVER_INFO_META_KEY]: serverInfo } } })}\n\n`);
```

**Flow:** POST subscriptions/listen → capacity guard PRE-ack (in-band −32603 on 200) → filter parsed through the era codec → honored subset computed against declared capabilities → SSE Response opens; ack first; keep-alive timer (~15s default) writes comment frames → bus publishes typed events (`tools_list_changed`, `resource_updated{uri}`, …) → per-stream listener filters via `listenFilterAccepts` (exact-URI match for resource subscriptions) → frames stamped with the subscription id → abort signal or closeAll tears down with unsubscribe→timer-clear→controller.close.

**Invariant:** Throwing listeners never stop bus delivery to others (per-listener try/catch with error sink); self-unsubscribe mid-dispatch is safe (Set iteration snapshot). The empty-result-before-close is THE graceful-close contract — clients must not reconnect-loop on it. Capabilities are REQUIRED at serve() so the ack can always be narrowed.

**Probe:** `test/e2e/scenarios/subscriptions.test.ts` :159 ("ack is the first frame … carrying the honored subset"), :171 ("delivers only opted-in change types"), :228 ("graceful-close signal"), :264 ("legacy-classified listen never reaches the entry router").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "createListenRouter honoredSubset listenFilterAccepts", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt ack-first/narrowed-filter/idempotent-teardown SSE routing for any change-notification surface; adapt event taxonomy and keep-alive defaults; omit the stdio twin unless you mirror subscriptions there.
