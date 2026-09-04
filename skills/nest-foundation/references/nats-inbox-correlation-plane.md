<!-- capsule-v2 -->
# NATS inbox correlation — how do you implement request/reply over a broker with no reply-topic concept?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When the broker has no durable reply channel (NATS), where does the reply go — and how do you keep N concurrent requests from cross-wiring their responses?

## Per-message reply token + per-request inbox
**Path/Symbol:** `packages/microservices/server/server-nats.ts:ServerNats.getPublisher` (183-201), `ServerNats.bindEvents` (80-95); `packages/microservices/client/client-nats.ts:ClientNats.publish` (232-267), `ClientNats.createSubscriptionHandler` (194-229).
**Signature:** `getPublisher(natsMsg: NatsMsg, id: string, ctx: NatsContext): (response: any) => void`; `publish(partialPacket: ReadPacket, callback: (packet: WritePacket) => any): () => void`.
**Data Shape:** server side — reply rides `natsMsg.reply` (the per-message reply token); client side — one fresh inbox subject per outstanding request via `natsPackage.createInbox(options.inboxPrefix)`; teardown fn unsubscribes that inbox.

### Decisive source
```ts
// ServerNats — the publisher IS the message's own reply token; no topic exists:
public getPublisher(natsMsg: NatsMsg, id: string, ctx: NatsContext) {
  if (natsMsg.reply) {
    return (response: any) => {
      Object.assign(response, { id });
      const outgoingResponse: NatsRecord = this.serializer.serialize(response);
      this.onProcessingEndHook?.(this.transportId, ctx);
      return natsMsg.respond(outgoingResponse.data, { headers: outgoingResponse.headers });
    };
  }
  return () => {};   // no reply token ⇒ event; noop publisher
}

// ClientNats — subscribe to a fresh inbox BEFORE publishing the request:
const inbox = natsPackage.createInbox(this.options.inboxPrefix);
const subscription = this.natsClient!.subscribe(inbox, { callback: subscriptionHandler });
this.natsClient!.publish(channel, serializedPacket.data, { reply: inbox, headers });
return () => subscription.unsubscribe();
```

**Flow:** client publish ⇒ assignPacketId ⇒ serialize ⇒ createInbox ⇒ subscribe(inbox) ⇒ publish(channel, data, {reply: inbox}) ⇒ server handleMessage deserializes with `{channel, replyTo}` ⇒ undefined id ⇒ handleEvent, else handler lookup (missing ⇒ publish `{id, status:'error', err:NO_MESSAGE_HANDLER}` on the reply token) ⇒ response$ drained through base Server.send into the per-message publisher. Client subscription handler ladder: transport error ⇒ callback({err}); EMPTY data (length 0 — NATS's "no responders" signal) ⇒ EmptyResponseException(normalized pattern) + isDisposed:true; `message.id !== packet.id` ⇒ DROP; isDisposed||err ⇒ terminal callback; else bare callback.
**Invariant:** exactly one inbox per outstanding request and it is subscribed before the request is published, so a reply can never arrive before its waiter exists; an empty reply body is a TERMINAL error (EmptyResponseException), never a hang; queue-group subscriptions (`client.subscribe(channel, {queue})` with queue = handler.extras?.queue ?? options.queue) make same-name servers share work while differently-named ones fan out.
**Probe:** `packages/microservices/test/client/client-nats.spec.ts` (publish pins publish(channel) + dispose unsubscribes + header merge arms; createSubscriptionHandler pins not-completed / disposed-correct-id / disposed-wrong-id-drop) and `test/server/server-nats.spec.ts` (bindEvents pins per-pattern queue override; getPublisher pins respond-on-reply-token and noop-without-reply; close pins gracefulShutdown ⇒ unsubscribe-all + waitForGracePeriod).
**Runner caveat:** repo deps uninstalled (vitest blocked); expectations quoted from spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", file_pattern: "server-nats.ts", fields: ["lines"], limit: 40 });
// expected @ pin: bindEvents 80-95, getPublisher 183-201, close 110-122
await mcp.codebase_memory.search_graph({ project: "nest", qn_pattern: ".*microservices.client.client-nats.ClientNats.publish", limit: 10 });
```

## Verdict
Adopt "per-request ephemeral reply channel created before the request leaves" as the general pattern for brokers without reply topics (NATS inboxes, gRPC call objects, AMQP direct reply-to all solve the same race differently). Adopt the empty-body⇒terminal-error rule for any broker that signals "no responders" with an empty message. Adapt the queue-group option to your broker's work-sharing primitive; omit it entirely for point-to-point transports. Omit the gracefulShutdown grace period (default 10s) if your deployment tears down via orchestrator signals instead of in-process close().
