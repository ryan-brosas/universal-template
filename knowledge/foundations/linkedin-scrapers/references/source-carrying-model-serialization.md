<!-- capsule-v2 -->
# Source-carrying model serialization — how do I hydrate rich domain objects from a data source that must survive the round-trip, without globals or factories?

**Source:** lh-basis ISC (core/models package.json) — patterns only, dist-compiled tree; Codebase Memory `lh-basis` (models plane EXCLUDED by design → source-read probes only). **Question:** How does class-transformer-based hydration re-attach a live `source` (DB/API handle) to every deserialized object when decorators have no access to it?

## The ambient context trick
**Path/Symbol:** `core/models/dist/services/deserializationContext.ts:DeserializationContext`; `core/models/dist/models/helpers/SerializableWithSource.ts:SerializableWithSource` + `hasSourceProperty/getExistingContextKeyFromTransformParams`; `core/models/dist/helpers/SuperJSONTransform.ts:SuperJSONTransform`.
**Signature:** `DeserializationContext.getInstance().withContext(context: {source}, operation: (contextKey) => T): T`; decorator `@SuperJSONTransform()` on the property holding serialized state.
**Data Shape:** contextKey is an empty `{}` used as an unguessable WeakMap key; context = `{ source }`.

### Decisive source
```ts
// serialize: parent MUST carry source
if (!hasSourceProperty(obj)) throw new Error('Parent object must have source property');
const serializer = Serializer.create(() => obj.source);
return serializer.serialize(value);

// deserialize: resolve the SAME source through the ambient context
const contextKey = getExistingContextKeyFromTransformParams({ options }); // throws 'Context key not provided'
const source = DeserializationContext.getInstance().getContext(contextKey).source;
return serializer.deserialize(value);

// the property itself:
@Exclude({ toPlainOnly: true })   // never written to JSON
@Expose({ toClassOnly: true })    // always re-created on hydrate
@Transform((params) => DeserializationContext.getInstance()
    .getContext(getExistingContextKeyFromTransformParams(params)).source, { toClassOnly: true })
source: Object;
```

**Flow:** wrap EVERY `plainToClass` call in `withContext({source}, key => plainToClass(Cls, json, { __contextKey: key }))` → during hydration the `source` property's Transform pulls the source out of the WeakMap via options-planted `__contextKey` → resulting instance holds a live handle while looking like a plain DTO. Class registry twin (`serializableModelsRegistry.ts`): `@SerializableModel()` registers `Map<className, ctor>` so polymorphic payloads can be re-typed from their `$type`-style name.
**Invariant:** the WeakMap key is thrown away after the operation — no global state, concurrent deserializations can't cross-contaminate, and nothing about "current source" leaks into module scope. Serialization THROWS if a model without source is asked to serialize (loud over silent). The `Exclude(toPlainOnly)/Expose(toClassOnly)` pair makes `source` invisible in JSON yet mandatory at runtime.
**Probe:** NO tests exist for this plane (dist-only vendor artifact) — coverage caveat recorded; claims pinned by whole-file source reads at HEAD (no git pin; directory unchanged since pass 8) + graph exclusion verified via `index_status --verbose` (`not_indexed.dirs` lists all three dist trees).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "lh-basis", query: "SerializableWithSource", limit: 5, fields: ["signature", "name", "file"] }); // returns 0 — plane excluded by design
```

## Verdict
Adopt the withContext+WeakMap pattern whenever a deserializer must inject non-serializable dependencies into hydrated objects. Adapt to your transformer library (the shape ports to any visitor-style hydrator). Omit the SuperJSON value-format details (vendor-specific serializer).
