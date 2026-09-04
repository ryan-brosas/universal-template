<!-- capsule-v2 -->
# Kafka batch-by-wire-size producer — how do you stream events to Kafka without ever exceeding the broker's max message bytes?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are variable-size event messages batched so no send exceeds the size limit, and what happens on failure?

## kafka-wire-size-batching
**Path/Symbol:** `src/lib/kafka.ts:sendMessage :90-144` (+ getMaxMessageBytes :21-24, getMessages :30-37, connect :146-156).
**Signature:** `sendMessage(topic, msg|msg[]) -> Promise<RecordMetadata[]>`; DEFAULT_MAX_MESSAGE_BYTES=900_000 (env `KAFKA_MAX_MESSAGE_BYTES`), CONNECT_TIMEOUT=5000, SEND_TIMEOUT=3000, ACKS=1.
**Data Shape:** messages JSON-serialized once; per-message byte length via `Buffer.byteLength(value,'utf8')`.

### Decisive source
```ts
for (const { value, size } of messages) {
  if (size > maxMessageBytes) {                       // single monster record: DROP + log
    log('Kafka message dropped: topic=%s size=%d max=%d', topic, size, maxMessageBytes);
    continue;
  }
  if (batch.length && batchSize + size > maxMessageBytes) {   // would overflow ⇒ flush first
    result.push(...(await producer.send({ topic, messages: batch, timeout: SEND_TIMEOUT, acks: ACKS })));
    batch = []; batchSize = 0;
  }
  batch.push({ value }); batchSize += size;
}
if (batch.length) { result.push(...(await producer.send({ ... }))); }
} catch (e) {
  console.log('KAFKA ERROR:', serializeError(e));
  return [];                                          // FAIL-OPEN: analytics never blocks the request
}
```

**Flow:** connect lazily → serialize → greedy accumulate until the next message would cross the wire limit → flush → final flush; oversized singles are dropped with a log line.
**Invariant:** fail-open contract — a dead Kafka returns `[]`, never throws into the collect route. The pre-check `batchSize + size > max` runs BEFORE pushing (so a full batch never overflows), and acks=1 trades durability for latency by design.
**Probe:** structural pins at pin: `grep -n "Kafka message dropped" src/lib/kafka.ts` → :100; `grep -c "batchSize + size > maxMessageBytes" src/lib/kafka.ts` → 1.
**Probe:** `grep -n "900_000\|DEFAULT_MAX_MESSAGE_BYTES" src/lib/kafka.ts | head -2` → :9.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "sendMessage maxMessageBytes batch kafka", limit: 10 });
```

## Verdict
Adopt wire-size-aware greedy batching for any queue producer fed by untrusted payload sizes; adapt limits/acks to your broker config; keep the drop-with-log policy for poison records.
