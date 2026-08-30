<!-- capsule-v2 -->
# RMQ direct reply-to queue — how do you correlate N concurrent replies without per-request subscriptions?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When the broker offers a shared direct-reply channel (AMQP `amq.rabbitmq.reply-to`), how do you route each reply to its waiter, and what does the connection/channel setup look like for wildcard vs plain-queue modes?

## correlationId-keyed response emitter over one shared consumer
**Path/Symbol:** `packages/microservices/client/client-rmq.ts:ClientRMQ.publish` (382-452), `consumeChannel` (253-263), `setupChannel` (211-251), `mergeDisconnectEvent` (169-198); `REPLY_QUEUE` constant (56).
**Signature:** `publish(message: ReadPacket, callback: (packet: WritePacket) => any): () => void`; `consumeChannel(channel: Channel): Promise<void>`.
**Data Shape:** ONE consumer on `amq.rabbitmq.reply-to` emits every reply into `responseEmitter` keyed by `msg.properties.correlationId`; `responseEmitter.setMaxListeners(0)` because N concurrent requests each hold one listener; sendOptions = `{replyTo, persistent(default false), ...liftedOptions, headers, correlationId}`.

### Decisive source
```ts
const REPLY_QUEUE = 'amq.rabbitmq.reply-to';

// consumeChannel — one shared consumer fans out by AMQP correlationId:
await channel.consume(this.replyQueue,
  (msg: ConsumeMessage | null) => this.responseEmitter.emit(msg!.properties.correlationId, msg),
  { noAck });   // noAck default true

// publish — listener registered BEFORE the send; record options lifted into sendOptions:
const correlationId = randomStringGenerator();
Object.assign(message, { id: correlationId });
const serializedPacket = this.serializer.serialize(message);
const options = serializedPacket.options;
delete serializedPacket.options;
this.responseEmitter.on(correlationId, listener);
const sendOptions = { replyTo: this.replyQueue, persistent: ..., ...options,
  headers: this.mergeHeaders(options?.headers), correlationId };
// wildcard/fanout ⇒ channel.publish(exchange, stringifiedPattern, content, sendOptions)
// else          ⇒ channel.sendToQueue(this.queue, content, sendOptions)
return () => this.responseEmitter.removeListener(correlationId, listener);
```

**Flow:** connect() memoizes on `this.client`, registers error/disconnect/connect/blocked/unblocked listeners, drains pendingEventListeners parked pre-connect; source$ = merge(connect$-with-disconnect-as-error, reconnect-events skip(1)) into ReplaySubject(1) = connection$. setupChannel branching: `!wildcards && exchangeType!=='fanout'` ⇒ assertQueue(queue, queueOptions) unless noAssert + bindQueue(exchange, routingKey, '' when fanout); else assertExchange(exchange||queue, exchangeType||'topic', {durable:true, arguments}); then prefetch(prefetchCount default 0, isGlobalPrefetchCount default false) + consumeChannel. Reply arrives ⇒ handleMessage deserializes (parseMessageContent = JSON.parse with raw-string fallback) ⇒ isDisposed||err ⇒ terminal callback else bare callback; teardown removes the correlationId listener.
**Invariant:** the waiter is registered BEFORE the request is sent (no lost first reply); exactly one shared reply consumer exists for the whole client lifetime (contrast NATS inbox-per-request and MQTT topic-per-pattern); multi-URL failover is BOUNDED — 'connectFailed' retries only while error.url is not the last entry of options.urls, then throws; blocked/unblocked broker events surface as RmqStatus.BLOCKED/UNBLOCKED.
**Probe:** `packages/microservices/test/client/client-rmq.spec.ts` (setupChannel pins assertQueue/bindQueue suppression arms for noAssert/fanout/wildcards + prefetch args; publish pins sendToQueue vs exchange-publish, dispose removes listener, header merge arms; handleMessage pins error/disposed/response callback shapes).
**Runner caveat:** repo deps uninstalled (vitest blocked); expectations quoted from spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", file_pattern: "client-rmq.ts", fields: ["lines"], limit: 40 });
// expected @ pin: REPLY_QUEUE 56, setupChannel 211-251, consumeChannel 253-263, publish 382-452
await mcp.codebase_memory.search_graph({ project: "nest", qn_pattern: ".*microservices.client.client-rmq.ClientRMQ.mergeDisconnectEvent", limit: 10 });
```

## Verdict
Adopt "one shared reply consumer + correlationId-keyed emitter with unlimited listeners" as the cheapest correlation scheme when the broker provides a direct reply-to facility — zero subscription churn at high concurrency. Adopt the register-listener-before-send ordering for any async correlation. Adapt the URL-ladder retry bound to your broker's failover list semantics; omit it for single-broker deployments. Omit the wildcard/fanout exchange branch unless your routing keys contain wildcards (it changes both topology assertions and the publish call).
