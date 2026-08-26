<!-- capsule-v2 -->
# IncomingRequestDeserializer isExternal ladder — how do you accept BOTH enveloped internal packets and raw external payloads with one deserializer?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How can a transport server deserialize messages that may arrive either as a framework `{id, pattern, data}` envelope or as a bare broker payload, without losing the routing key?

## Falsy⇒external, has-pattern-or-data⇒internal, else map channel→pattern
**Path/Symbol:** `packages/microservices/deserializers/incoming-request.deserializer.ts:IncomingRequestDeserializer` (11-50; `deserialize` 12-20, `isExternal` 22-33, `mapToSchema` 35-49); role-based default install `packages/microservices/server/server.ts:Server.initializeDeserializer` (318-329); subclass override `packages/microservices/deserializers/kafka-request.deserializer.ts:KafkaRequestDeserializer` (8-24).
**Signature:** `deserialize(value: any, options?: Record<string, any>): IncomingRequest | IncomingEvent | Promise<...>`; `isExternal(value: any): boolean`; `mapToSchema(value, options?)`.
**Data Shape:** input = raw broker message + per-message `options` (transports put the topic/channel under `options.channel`); output = `{pattern, data}` where both may be `undefined` when options are absent.

### Decisive source
```ts
deserialize(value, options?) {
  return this.isExternal(value) ? this.mapToSchema(value, options) : value;
}
isExternal(value) {
  if (!value) return true;                              // falsy ⇒ treat as foreign
  if (!isUndefined(value.pattern) || !isUndefined(value.data)) {
    return false;                                       // already an envelope ⇒ passthrough
  }
  return true;
}
mapToSchema(value, options?) {
  if (!options) return { pattern: undefined, data: undefined };
  return { pattern: options.channel, data: value };     // THE PATTERN IS THE CHANNEL
}
```

**Flow:** every inbound server message hits `deserializer.deserialize(raw, {channel})`. A truthy object carrying a defined `pattern` OR `data` key is assumed to be a native packet and returned by reference (spec pins `.toBe` identity). Anything else — including `null`, `0`, or a plain `{array:[1,2,3]}` payload from a non-nest producer — is wrapped, taking its route name from `options.channel`. The default pair is installed once per server (`IdentitySerializer` + this deserializer via `options.deserializer || new IncomingRequestDeserializer()`), so user-supplied codecs win through the `||`.
**Invariant:** the internal-passthrough test must check key PRESENCE (`!isUndefined`), not truthiness — an envelope with `data: undefined` must still be recognized as internal; and the mapped pattern must come from transport options, never guessed from the payload.
**Probe:** `packages/microservices/test/deserializers/incoming-request.deserializer.spec.ts` (envelope `{id,pattern,data}` returned unchanged by identity; `{array:[1,2,3]}` + `{channel:'test'}` → `{pattern:'test', data:<payload>}`; no options → `{pattern: undefined, data: undefined}`).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec source read directly.

## Subclass reuse pattern
`KafkaRequestDeserializer extends IncomingRequestDeserializer` overriding ONLY `mapToSchema` to unwrap `data?.value ?? data` while inheriting the whole isExternal ladder — port new transports by overriding the mapping half, not the detection half.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "incoming request deserializer external pattern channel", limit: 10 });
// live @ pin: rank#1-3 IncomingRequestDeserializer.isExternal/deserialize/mapToSchema (deserializers/incoming-request.deserializer.ts 22-33/12-20/35-49)
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "nest.packages.microservices.deserializers.incoming-request.deserializer.IncomingRequestDeserializer.deserialize", direction: "inbound", depth: 2 });
// live @ pin: subclass NatsRequestJSONDeserializer.deserialize extends it — ladder is inherited family-wide
```

## Verdict
Adopt the two-arm deserializer (detection vs mapping split, presence-not-truthiness envelope test, channel-as-pattern default) for any bridge between structured RPC envelopes and schema-less brokers. Adapt `options.channel` to your transport's route carrier and extend via mapToSchema overrides like Kafka does. Omit the Promise branch only if all your codecs are synchronous.
