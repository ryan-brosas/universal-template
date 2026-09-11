<!-- capsule-v2 -->
# Kafka client reply-topic pinning — how does a consumer-group client guarantee its own replies come back to a partition it is assigned, and what must happen before connect()?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you make request/reply work for a client that shares a consumer group, where a naive reply topic could be consumed by another member?

## Minimum-partition pinning over `${pattern}.reply`
**Path/Symbol:** `packages/microservices/client/client-kafka.ts:ClientKafka.publish` (372-412), `subscribeToResponseOf` (123-126), `bindTopics` (177-195), `createResponseCallback` (214-243), `setConsumerAssignments` (418-431), `getReplyTopicPartition` (362-370); assignor `packages/microservices/helpers/kafka-reply-partition-assigner.ts:KafkaReplyPartitionAssigner` (14-200).
**Signature:** `publish(partialPacket: ReadPacket, callback: (packet: WritePacket) => any): () => void`; `getReplyTopicPartition(topic: string): string`.
**Data Shape:** `responsePatterns: string[]` (`${normalizedPattern}.reply`); `consumerAssignments: {[topic]: number}` (MIN partition per topic); reply headers CORRELATION_ID = packet id, REPLY_TOPIC, REPLY_PARTITION.

### Decisive source
```ts
protected getReplyTopicPartition(topic: string): string {
  const minimumPartition = this.consumerAssignments[topic];
  if (isUndefined(minimumPartition)) throw new InvalidKafkaClientTopicException(topic);
  return minimumPartition.toString();               // MIN assigned partition of OUR group member
}

protected setConsumerAssignments(data: ConsumerGroupJoinEvent): void {
  const consumerAssignments = {};
  // Only need to set the minimum
  for (const [topic, memberPartitions] of Object.entries(data.payload.memberAssignment)) {
    if (memberPartitions.length) consumerAssignments[topic] = Math.min(...memberPartitions);
  }
  this.consumerAssignments = consumerAssignments;
}

// publish — slot reserved BEFORE the async chain; sync + async failures both funnel:
const packet = this.assignPacketId(partialPacket);
this.routingMap.set(packet.id, callback);
const cleanup = () => this.routingMap.delete(packet.id);
const errorCallback = (err: unknown) => { cleanup(); callback({ err }); };
try {
  ...
  Promise.resolve(this.serializer.serialize(packet.data, { pattern }))
    .then((serializedPacket: KafkaRequest) => {
      serializedPacket.headers[KafkaHeaders.CORRELATION_ID] = packet.id;
      serializedPacket.headers[KafkaHeaders.REPLY_TOPIC] = replyTopic;
      serializedPacket.headers[KafkaHeaders.REPLY_PARTITION] = replyPartition;
      return this._producer!.send({ topic: pattern, messages: [serializedPacket], ... });
    })
    .catch(err => errorCallback(err));
  return cleanup;
} catch (err) { errorCallback(err); return () => null; }
```

**Flow:** callers MUST `subscribeToResponseOf(pattern)` before `connect()` — bindTopics subscribes the `.reply` topics and runs `createResponseCallback` as eachMessage → GROUP_JOIN fires `setConsumerAssignments`, storing the MINIMUM assigned partition per topic (empty assignments omitted) → publish pins REPLY_PARTITION to that min so the server writes the reply onto a partition THIS member consumes; the custom assignor closes the loop by honoring previous assignments (round-tripped through member userData JSON via `getConsumerAssignments`), taking min partitions first, filling zero-partition members, then round-robining the rest. Responses drop silently when the message has no CORRELATION_ID header (other members' traffic) or the id is unknown in routingMap; `err || isDisposed` terminalizes the callback.
**Invariant:** publish without a subscribed/assigned reply topic throws `InvalidKafkaClientTopicException` instead of silently losing replies; the routingMap slot exists before any async step and every failure path (sync throw AND promise rejection) removes it and reports `{err}` once.
**Probe:** `packages/microservices/test/client/client-kafka.spec.ts` — setConsumerAssignments pins MIN (`{'topic-a': 0, 'topic-b': 3}`, empty omitted); createResponseCallback five arms (normal / disposed / error-header / no-correlation-id drop / wrong-id drop); publish pins all three headers + pre-send routingMap.set + unsubscribe teardown removal + send-throw → callback err; getReplyTopicPartition throw arms; connect memoization + producer-only mode.
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", file_pattern: "client-kafka.ts", fields: ["lines"], limit: 30 });
// live @ pin: publish 372-412, createResponseCallback 214-243, setConsumerAssignments 418-431, emitBatch 249-265
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "nest.packages.microservices.client.client-kafka.ClientKafka.createResponseCallback", direction: "outbound", depth: 2 });
```

## Verdict
Adopt min-partition pinning verbatim for shared-group reply consumption on any partitioned log transport — it converts "someone in my group will get it" into "my assignment definitely covers this reply"; adopt subscribe-before-connect + fail-fast on unknown reply topics so misconfiguration surfaces at first send, not as a silent timeout. Adapt the assignor's stickiness policy to your rebalancing goals (it deliberately accepts imbalance: documented "This process can result in imbalanced assignments"). Omit producerOnlyMode and emitBatch unless you need them; if you add batching, mirror emitBatch's hot-connectable-over-defer shape.
