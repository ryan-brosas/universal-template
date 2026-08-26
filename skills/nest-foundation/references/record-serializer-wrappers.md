<!-- capsule-v2 -->
# Record serializer wrappers — how do per-message publish options travel when the payload channel can only carry bytes?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do RmqRecord/MqttRecord/NatsRecord builder objects get their transport options (persistent, qos, headers) delivered to the broker without polluting the application payload?

## Unpack INTO the packet; each transport lifts what ITS client can consume
**Path/Symbol:** `packages/microservices/serializers/rmq-record.serializer.ts:RmqRecordSerializer` (6-25); `packages/microservices/serializers/mqtt-record.serializer.ts:MqttRecordSerializer` (5-16); `packages/microservices/serializers/nats-record.serializer.ts:NatsRecordSerializer` (6-23); builders `packages/microservices/record-builders/{rmq,mqtt,nats}.record-builder.ts`.
**Signature:** `serialize(packet: ReadPacket): ReadPacket & Partial<RmqRecord> | string | NatsRecord`.
**Data Shape:** input packet `{pattern, data}` where `data` may be a `<X>Record` instance built via `<X>RecordBuilder`; outputs differ per transport: RMQ = spread packet with lifted `options`; MQTT = JSON string; NATS = `{data: JSON-string, headers}`.

### Decisive source
```ts
// RMQ: lift options to TOP LEVEL of the packet — ServerRMQ turns them into AMQP sendOptions
serialize(packet) {
  if (packet?.data && isObject(packet.data) && packet.data instanceof RmqRecord) {
    const record = packet.data;
    return { ...packet, data: record.data, options: record.options };
  }
  return packet;                                   // identity passthrough (.toBe-pinned)
}

// MQTT: JSON-stringify whole packet with data unpacked; MqttRecord OPTIONS DROPPED
serialize(packet): string {
  if (isObject(packet?.data) && packet.data instanceof MqttRecord) {
    const record = packet.data;
    return JSON.stringify({ ...packet, data: record.data });
  }
  return JSON.stringify(packet);
}

// NATS: wrap-or-reuse record for headers, JSON body
serialize(packet): NatsRecord {
  const natsMessage =
    packet?.data && isObject(packet.data) && packet.data instanceof NatsRecord
      ? packet.data
      : new NatsRecordBuilder(packet?.data).setHeaders(packet?.headers).build();
  return {
    data: JSON.stringify({ ...packet, data: natsMessage.data }),
    headers: natsMessage.headers,
  };
}
```

**Flow:** all three follow one rule — the record object is UNPACKED into the outgoing packet, never nested. Where the options go is transport-specific: RMQ lifts them to `packet.options` because `ServerRMQ.sendMessage` strips `.options` into AMQP `sendOptions` (`{correlationId, ...options}`); MQTT silently discards them from the wire envelope (spec: "ignoring options") because publish-level qos/dup/retain must flow through the mqtt client's publish call, not the payload — the serializer only guarantees the payload stays decodable; NATS keeps them OUT of the JSON body in a parallel `headers` field, wrapping raw packets so header-less sends still produce a valid `{data, headers}` pair.
**Invariant:** non-record payloads pass through UNCHANGED semantics (RMQ by reference — spec pins `.toBe`; MQTT/NATS still stringify since their transports require strings); the application-visible `data` after serialization is always the BUILDER's `.data`, never the record wrapper itself.
**Probe:** `packages/microservices/test/serializers/rmq-record.serializer.spec.ts` (RmqRecordBuilder data+options → `{pattern, options:{appId,persistent}, data:{value}}`; plain packet → same reference) and `mqtt-record.serializer.spec.ts` (record with QoS/dup/retain/properties → exactly `JSON.stringify({pattern:'pattern', data:{value:'string'}})` — options absent; plain packet → `JSON.stringify(packet)`).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "kafka request response serializer record serialize encode", limit: 10 });
// live @ pin: rank#3/#4 MqttRecordSerializer.serialize(6-15) / RmqRecordSerializer.serialize(10-24)
await mcp.codebase_memory.get_code_snippet({ project: "nest", qualified_name: "nest.packages.microservices.serializers.nats-record.serializer.NatsRecordSerializer.serialize" });
// live @ pin: wrap-or-reuse ladder retrieved verbatim (10-22)
```

## Verdict
Adopt the unpack-don't-nest rule and the "each transport consumes only what its publish call accepts" split for any broker with per-message metadata. Adapt option placement to your client API surface (top-level fields vs side-channel headers vs call arguments). Omit the MQTT options-drop at your peril: serializing them into the payload would corrupt every non-nest consumer on the topic.
