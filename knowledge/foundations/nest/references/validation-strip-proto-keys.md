<!-- capsule-v2 -->
# stripProtoKeys — how is prototype pollution blocked, and why does the stripper skip Date/RegExp/Map instances?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Which keys get deleted from incoming payloads, in what order, and which objects must be left untouched for test frameworks to keep working?

## ValidationPipe.stripProtoKeys / StandardSchemaValidationPipe.stripProtoKeys
**Path/Symbol:** `packages/common/pipes/validation.pipe.ts:stripProtoKeys` (:299-333); duplicated verbatim at `packages/common/pipes/standard-schema-validation.pipe.ts:175-206`; guard list `BUILT_IN_TYPES = [Date, RegExp, Error, Map, Set, WeakMap, WeakSet]` (validation.pipe.ts :63, standard-schema pipe :19).
**Signature:** `protected stripProtoKeys(value: any): void` — recursive, mutates in place.
**Data Shape:** Input is the raw request payload (body/query object tree). Uses `util.types.isTypedArray` for the typed-array bail.

### Decisive source
```ts
if (value == null || typeof value !== 'object' || types.isTypedArray(value)) return;
// Skip built-in JavaScript primitives to avoid Jest useFakeTimers conflicts
if (BUILT_IN_TYPES.some(type => value instanceof type)) return;
if (Array.isArray(value)) { for (const v of value) this.stripProtoKeys(v); return; }

delete value.__proto__;
delete value.prototype;
const constructorType = value?.constructor;
if (constructorType && !BUILT_IN_TYPES.includes(constructorType)) {
  delete value.constructor;   // ONLY when constructor isn't a built-in type
}
for (const key in value) this.stripProtoKeys(value[key]);
```

**Flow:** bail on null/non-object/typed-array → bail on built-in INSTANCES → recurse arrays element-wise → delete `__proto__` and `prototype` unconditionally → delete `constructor` only if it isn't one of the seven built-ins → recurse own enumerable keys.
**Invariant:** `delete value.__proto__` on an ordinary own property only SHADOWS the getter — a payload like `{"__proto__": {...}}` parsed by JSON has an own enumerable `__proto__`, and deleting it prevents the merge-into-Object.prototype attack; but the built-in exemption is load-bearing: `new Date()` passes through `useFakeTimers` proxies in Jest and any user field holding a Map/Set survives. The conditional `constructor` delete exists because stripping `Date.prototype.constructor` chains breaks instanceof-style checks downstream. Order matters: `__proto__`/`prototype` first, `constructor` second, THEN recursion — recursing before deletion would walk attacker-controlled prototype chains.
**Probe:** `packages/common/test/pipes/validation.pipe.spec.ts` — "when validation strips" (:430 "should return a TestModel without extra properties") and "when validation rejects" :443 (payload with forbidden props); StandardSchema twin pinned via its shared implementation.
**Coverage caveat:** no dedicated spec file for stripProtoKeys edge cases (built-in exemptions are comment-documented regression fixes, not directly asserted) — source-grounded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "stripProtoKeys BUILT_IN_TYPES prototype pollution", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exact bail order + the seven-type exemption set as a security boundary (both pipes carry identical copies — port BOTH or extract one helper); adapt key names to your router's parser (`__proto__` handling differs for query-string parsers like qs); omit nothing. Porting wrong: unconditionally deleting `constructor` breaks DTOs holding Date/Map fields under fake timers; skipping the stripper entirely reopens `__proto__` pollution through class-transformer's plainToInstance merge.
