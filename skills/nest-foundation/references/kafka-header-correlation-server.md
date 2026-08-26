<!-- capsule-v2 -->
# Kafka server header correlation + retriable replay — how does request/reply work when the broker has no reply queues, and how can a handler ask for redelivery mid-stream?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you route replies, mark terminals, and trigger broker-level retries over a log-based transport where correlation cannot live in a routing map on the wire?

## Headers are the envelope; the topic is the pattern
**Path/Symbol:** `packages/microservices/server/server-kafka.ts:ServerKafka.handleMessage` (262-318), `combineStreamsAndThrowIfRetriable` (336-362), `sendMessage` + header assignors (364-428), RegExp-aware `addHandler` (83-110) and `getHandlerByPattern`/`isPatternMatch` (212-240).
**Signature:** `handleMessage(payload: EachMessagePayload)`; `combineStreamsAndThrowIfRetriable(response$: Observable<any>, replayStream$: ReplaySubject<unknown>): Promise<void>`; `sendMessage(message: OutgoingResponse, replyTopic, replyPartition, correlationId, context)`.
**Data Shape:** inbound headers `CORRELATION_ID` / `REPLY_TOPIC` / `REPLY_PARTITION`; outbound headers `CORRELATION_ID` / `NEST_ERR` / `NEST_IS_DISPOSED` (`Buffer.alloc(1)` sentinel); registered pattern keys double as consumer topics.

### Decisive source
```ts
const correlationId = headers[KafkaHeaders.CORRELATION_ID];
const replyTopic    = headers[KafkaHeaders.REPLY_TOPIC];
const replyPartition = headers[KafkaHeaders.REPLY_PARTITION];

const handler = this.getHandlerByPattern(packet.pattern);
// if the correlation id or reply topic is not set then this is an event
if (handler?.isEventHandler || !correlationId || !replyTopic) {
  return this.handleEvent(packet.pattern, packet, kafkaContext);
}
const publish = this.getPublisher(replyTopic, replyPartition, correlationId, kafkaContext);
if (!handler) {
  return publish({ id: correlationId, err: NO_MESSAGE_HANDLER });   // requests still get a reply
}
...
const replayStream$ = new ReplaySubject();
await this.combineStreamsAndThrowIfRetriable(response$, replayStream$);
this.send(replayStream$, publish);

private combineStreamsAndThrowIfRetriable(response$, replayStream$) {
  return new Promise<void>((resolve, reject) => {
    let isPromiseResolved = false;
    response$.subscribe({
      next: val => { replayStream$.next(val); if (!isPromiseResolved) { isPromiseResolved = true; resolve(); } },
      error: err => {
        if (err instanceof KafkaRetriableException && !isPromiseResolved) { isPromiseResolved = true; reject(err); }
        else { resolve(); }                                  // non-retriable ⇒ still ship it as NEST_ERR
        replayStream$.error(err);
      },
      complete: () => replayStream$.complete(),
    });
  });
}

public assignIsDisposedHeader(outgoingResponse, outgoingMessage) {
  if (!outgoingResponse.isDisposed) return;
  outgoingMessage.headers![KafkaHeaders.NEST_IS_DISPOSED] = Buffer.alloc(1);
}
```

**Flow:** eachMessage → parser clones message+headers (`KafkaParser` — "modifying the original would break KafkaJS retries"; leading-zero-byte first byte passes schema payloads through untouched) → deserialize with `{channel: topic}` so the TOPIC is the pattern → event-vs-message decision (`isEventHandler || missing correlation/reply` arms all spec-pinned) → request path bridges handler stream into a ReplaySubject whose awaiting promise resolves on FIRST value (send starts mid-stream) but rejects pre-value on `KafkaRetriableException`, throwing back into eachMessage so kafkajs redelivers → every outbound packet gets partition pinned from REPLY_PARTITION (`parseFloat`, only when present), CORRELATION_ID always, NEST_ERR only on error (stringified if object), NEST_IS_DISPOSED sentinel only on terminal.
**Invariant:** a request without a handler STILL publishes an error reply to the reply topic (never silent, never nacked); retriable throws before the first value never reach the wire; regex handler patterns are stored raw by the Kafka-only addHandler override and matched linearly with `lastIndex` reset BEFORE and AFTER `.test()` (global-flag pollution guard).
**Probe:** `packages/microservices/test/server/server-kafka.spec.ts` — four event/message decision arms; `getPublisherSpy` called with `{id: correlationId.toString(), err: NO_MESSAGE_HANDLER}`; sendMessage wire pins incl. `{value:null, partition:parseFloat('0'), headers:{NEST_ERR: Buffer.from(NO_MESSAGE_HANDLER)}}` and `NEST_IS_DISPOSED: Buffer.alloc(1)`; bindEvents subscribes `[pattern]` topics and passes run options through.
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", name_pattern: "combineStreamsAndThrowIfRetriable|assignCorrelationIdHeader", fields: ["lines"], limit: 10 });
// live @ pin: rank#1 ServerKafka.assignCorrelationIdHeader 412-418, rank#2 ServerKafka.combineStreamsAndThrowIfRetriable 336-362
```

## Verdict
Adopt header-based correlation verbatim for any log-based transport (correlation id + reply destination + terminal/error flags travel WITH the message; body stays pure payload); adopt the resolve-on-first-value replay bridge whenever you want streaming responses over a send-per-value API while preserving a pre-first-value retry window. Adapt the retriable exception class to your broker's redelivery contract and the Buffer-typed header sentinels to your wire format. Omit the RegExp registry branch unless users need topic-pattern handlers — if you keep it, keep the lastIndex reset guard.
