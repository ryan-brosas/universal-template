<!-- capsule-v2 -->
# MQTT reply-topic refcount — how do you guarantee the reply subscription is active before the request can be answered?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When replies arrive on a fixed derived topic (`${pattern}/reply`) shared by many concurrent requests, how do you subscribe exactly once per topic while still giving every request its own waiter — and why must the publish happen INSIDE the subscribe callback?

## Subscribe-then-publish ordering + refcounted channel subscriptions
**Path/Symbol:** `packages/microservices/client/client-mqtt.ts:ClientMqtt.publish` (226-275), `getResponsePattern` (62-64), `unsubscribeFromChannel` (296-303), `createResponseCallback` (202-224), `mergePacketOptions` (309-333).
**Signature:** `publish(partialPacket: ReadPacket, callback: (packet: WritePacket) => any): () => void`; `getResponsePattern(pattern: string): string`.
**Data Shape:** `subscriptionsCount: Map<string, number>` refcounts per response channel; `routingMap` (inherited) holds one callback per packet id; MqttRecord options are lifted OUT of the payload before serialization.

### Decisive source
```ts
public getResponsePattern(pattern: string): string {
  return `${pattern}/reply`;
}

protected publish(partialPacket: ReadPacket, callback) {
  const packet = this.assignPacketId(partialPacket);
  const pattern = this.normalizePattern(partialPacket.pattern);
  const responseChannel = this.getResponsePattern(pattern);
  let subscriptionsCount = this.subscriptionsCount.get(responseChannel) || 0;

  const publishPacket = () => {
    subscriptionsCount = this.subscriptionsCount.get(responseChannel) || 0;
    this.subscriptionsCount.set(responseChannel, subscriptionsCount + 1);
    this.routingMap.set(packet.id, callback);          // waiter registered pre-publish
    const options = isObject(packet?.data) && packet.data instanceof MqttRecord
      ? packet.data.options : undefined;
    delete packet?.data?.options;                       // options never ride in the body
    const serializedPacket = this.serializer.serialize(packet);
    this.mqttClient!.publish(this.getRequestPattern(pattern), serializedPacket,
      this.mergePacketOptions(options));
  };

  if (subscriptionsCount <= 0) {
    this.mqttClient!.subscribe(responseChannel, (err: any) => !err && publishPacket());
  } else {
    publishPacket();
  }
  return () => {
    this.unsubscribeFromChannel(responseChannel);      // decrement; unsubscribe at zero
    this.routingMap.delete(packet.id);
  };
}
```

**Flow:** first request for a pattern ⇒ subscribe(`${pattern}/reply`) and publish ONLY in the subscribe success callback (a failed subscribe never sends the request); subsequent concurrent requests skip straight to publishPacket after incrementing the refcount. Reply ⇒ createResponseCallback JSON.parses the buffer, deserializes, looks up routingMap by id — unknown id dropped (shared-subscription traffic from other consumers), isDisposed||err terminal. Teardown decrements and unsubscribes at zero. mergePacketOptions merges global userProperties UNDER per-request ones and never emits an empty userProperties object (brokers drop such messages — issue #14079 cited in source).
**Invariant:** the reply subscription is guaranteed active before the first request for that pattern leaves the process (subscribe-callback ordering); N concurrent requests share ONE subscription but keep N routingMap slots (same refcount contract as redis-reply-refcount-reconnect); publish options (qos/dup/retain/properties) travel via the publish call, never inside the JSON payload; the 'message' handler is registered exactly once on connect (isInitialConnection latch) and ECONNREFUSED/ENOTFOUND errors are swallowed as transient.
**Probe:** `packages/microservices/test/client/client-mqtt.spec.ts` (publish pins subscribe-to-response-pattern + publish-to-request-pattern + routingMap entry + dispose unsubscribe/removal + header arms; getResponsePattern pins `/reply` suffix; createResponseCallback pins not-completed / disposed-correct-id / disposed-wrong-id-drop).
**Runner caveat:** repo deps uninstalled (vitest blocked); expectations quoted from spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", file_pattern: "client-mqtt.ts", fields: ["lines"], limit: 40 });
// expected @ pin: getResponsePattern 62-64, publish 226-275, unsubscribeFromChannel 296-303, mergePacketOptions 309-333
await mcp.codebase_memory.search_graph({ project: "nest", qn_pattern: ".*microservices.client.client-mqtt.ClientMqtt.createResponseCallback", limit: 10 });
```

## Verdict
Adopt "publish inside the subscribe-success callback" as the canonical fix for the subscribe-before-publish race on fixed reply topics — it costs one extra hop only on the first request per pattern. Adopt the refcount-map + per-id routingMap split (subscription count ≠ waiter count). Adapt the `${pattern}/reply` convention to your broker's topic grammar; omit it when the broker offers per-message reply tokens (NATS) or direct reply-to queues (AMQP). Keep the empty-userProperties guard if you target MQTT 5 brokers — an empty object there silently drops the message.
