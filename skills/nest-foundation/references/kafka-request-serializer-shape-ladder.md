<!-- capsule-v2 -->
# KafkaRequestSerializer shape ladder — when does a payload become JSON, toString(), or pass through untouched?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you coerce arbitrary JS values into Kafka-safe message values without destroying class instances that carry meaningful string representations?

## Wrap non-Kafka shapes, encode value/key, default headers {}
**Path/Symbol:** `packages/microservices/serializers/kafka-request.serializer.ts:KafkaRequestSerializer` (19-57; `serialize` 23-40, `encode` 42-56); KafkaMessage input interface `KafkaRequest` (10-14); transport install `packages/microservices/server/server-kafka.ts:ServerKafka.initializeSerializer` (449-452) / `packages/microservices/client/client-kafka.ts:ClientKafka.initializeSerializer` (433-436).
**Signature:** `serialize(value: any): KafkaRequest`; `encode(value: any): Buffer | string | null`.
**Data Shape:** output = KafkaJS message `{key?, value, headers}`; `value`/`key` ∈ Buffer | string | null; headers always an object (default `{}`).

### Decisive source
```ts
serialize(value) {
  const isNotKafkaMessage = isNil(value) || !isObject(value) ||
    (!('key' in value) && !('value' in value));
  if (isNotKafkaMessage) value = { value };        // wrap bare payloads
  value.value = this.encode(value.value);
  if (!isNil(value.key)) value.key = this.encode(value.key);
  if (isNil(value.headers)) value.headers = {};    // never leave headers undefined
  return value;
}
encode(value) {
  const isObjectOrArray = !isNil(value) && !isString(value) && !Buffer.isBuffer(value);
  if (isObjectOrArray) {
    return isPlainObject(value) || Array.isArray(value) ||
      value.toString == Object.prototype.toString   // block [object Object]
      ? JSON.stringify(value)
      : value.toString();                           // custom/inherited toString WINS
  } else if (isUndefined(value)) return null;
  return value;
}
```

**Flow:** nil / non-object / object lacking BOTH `key` and `value` ⇒ wrapped as `{value}` first (so an existing `{key, value}` Kafka message keeps its key). Then value (and non-nil key) go through `encode`: strings and Buffers pass through unchanged; `undefined` becomes `null` (Kafka has no undefined); plain objects and arrays stringify; any other object stringifies ONLY IF its `toString` is the inherited `Object.prototype.toString`, otherwise its custom `.toString()` output is preserved — including INHERITED custom toStrings, because the comparison is against the prototype's identity, not ownership. Spec pins all three branches: `Complex` → `'complex'`, `ComplexChild extends ComplexParent` → `'complexParent'`, `ComplexWithOutToString` → `'{"name":"complex"}'`.
**Invariant:** the `[object Object]` guard must compare `value.toString == Object.prototype.toString` (loose equality against the prototype function itself) — a naive `typeof value.toString === 'function'` test would stringify every class instance into garbage; numbers arrive as strings (`12345 → '12345'`) because encode treats them as objects with default toString? No — numbers are not string/buffer/nil so they take the object branch, fail plain/array/proto-toString, and hit `value.toString()` = `'12345'`.
**Probe:** `packages/microservices/test/serializers/kafka-request.serializer.spec.ts` (undefined/null → `{headers:{}, value:null}`; number → `'12345'`; buffer passes through bytewise; array → `'[1,2,3,4,5]'`; plain object → `'{"prop":"value"}'`; Complex/ComplexParent-inheritance/ComplexWithOutToString trio pins the toString ladder; kafka-message-with-key/headers arms pin the no-rewrap path).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "kafka request serializer record serialize encode", limit: 10 });
// live @ pin: rank#1/#2 KafkaRequestSerializer.encode(42-56)/serialize(23-40)
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "nest.packages.microservices.serializers.kafka-request.serializer.KafkaRequestSerializer.serialize", direction: "inbound", depth: 2 });
// live @ pin: callers = ServerKafka + ClientKafka sendMessage paths — same codec both directions
```

## Verdict
Adopt the three-way encode ladder verbatim for any broker whose values must be Buffer|string|null. Adapt the wrap predicate (`key in v || value in v`) to your envelope keys. Omit the Buffer passthrough only for text-only transports — but keep the Object.prototype.toString identity check wherever user classes may flow.
