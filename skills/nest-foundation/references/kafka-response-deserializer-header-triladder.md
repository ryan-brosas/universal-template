<!-- capsule-v2 -->
# KafkaResponseDeserializer header tri-ladder — how do correlation id, error, and stream termination ride alongside the payload?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you decode broker replies so that mid-stream values, terminal values, and remote errors all land in one response shape without a side channel?

## err header > disposed header > bare value, keyed by CORRELATION_ID
**Path/Symbol:** `packages/microservices/deserializers/kafka-response.deserializer.ts:KafkaResponseDeserializer.deserialize` (12-33); outbound counterpart `packages/microservices/server/server-kafka.ts:ServerKafka.sendMessage` (NEST_ERR / NEST_IS_DISPOSED / CORRELATION_ID producers, see `kafka-header-correlation-server.md`); consumer `ClientKafka.createResponseCallback` (214-243).
**Signature:** `deserialize(message: any, options?): IncomingResponse` where message = `{headers: Record<string|number, Buffer|string>, value: any}`.
**Data Shape:** headers used: `KafkaHeaders.CORRELATION_ID` (always), `KafkaHeaders.NEST_ERR`, `KafkaHeaders.NEST_IS_DISPOSED`; output = `{id: string, err? , response?, isDisposed: boolean}`.

### Decisive source
```ts
deserialize(message) {
  const id = message.headers[KafkaHeaders.CORRELATION_ID].toString();  // ALWAYS the key
  if (!isUndefined(message.headers[KafkaHeaders.NEST_ERR])) {
    return { id, err: message.headers[KafkaHeaders.NEST_ERR], isDisposed: true };
  }
  if (!isUndefined(message.headers[KafkaHeaders.NEST_IS_DISPOSED])) {
    return { id, response: message.value, isDisposed: true };
  }
  return { id, response: message.value, isDisposed: false };  // mid-stream frame
}
```

**Flow:** three arms in fixed priority — an error header wins over everything (and emits NO response field at all); a dispose header makes the payload terminal; neither ⇒ the value is a non-terminal frame of a streamed response. The correlation id is read unconditionally from the header and `.toString()`d, so routing survives Buffer-typed headers. This is what lets `combineStreamsAndThrowIfRetriable` + `createResponseCallback` keep a replay bridge open across multiple reply records until the terminal frame arrives.
**Invariant:** presence tests on headers use `!isUndefined`, never truthiness — a zero-length-buffer or empty-string sentinel must still count; the err arm MUST NOT also set `response` (spec pins `packet.response` undefined when NEST_ERR present) because observers branch on `response !== undefined && isDisposed`.
**Probe:** `packages/microservices/test/deserializers/kafka-response.deserializer.spec.ts` (CORRELATION_ID+NEST_ERR → `{id:'10', err:<same ref>, isDisposed:true, response undefined}`; CORRELATION_ID+NEST_IS_DISPOSED+value → `{id:'10', err undefined, isDisposed:true, response:'test'}`).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "nest", qualified_name: "nest.packages.microservices.deserializers.kafka-response.deserializer.KafkaResponseDeserializer.deserialize" });
// live @ pin: whole method retrieved verbatim (12-33)
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "nest.packages.microservices.client.client-kafka.ClientKafka.createResponseCallback", direction: "both", depth: 1 });
// live @ pin: consumes this output; drops headerless/unknown-id messages before consulting it
```

## Verdict
Adopt the priority-ordered header triad (error > dispose > stream-frame) plus unconditional correlation-id decoding for any multi-frame reply protocol. Adapt header names to your broker's metadata carrier (AMQP properties, MQTT user properties). Omit the no-response-on-error arm only if your observer ladder doesn't multiplex on `response !== undefined`.
