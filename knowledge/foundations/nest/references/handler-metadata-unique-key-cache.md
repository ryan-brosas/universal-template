<!-- capsule-v2 -->
# HandlerMetadataStorage — per-controller+method cache keyed by injected unique id, not class name

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Why is the handler-metadata cache key not the controller class name, and what breaks if a porter "simplifies" it?

## getMetadataKey / CONTROLLER_ID_KEY
**Path/Symbol:** `packages/core/helpers/handler-metadata-storage.ts:getMetadataKey` (:61-65), storage map (:49-59); `packages/core/injector/module.ts:assignControllerUniqueId` (:531-539).
**Signature:** `private getMetadataKey(controller, methodName): string`; `set(controller, methodName, metadata)` / `get(controller, methodName)`.
**Data Shape:** `Map<string, TValue>` hidden behind computed symbol property `HANDLER_METADATA_SYMBOL = Symbol.for('handler_metadata:cache')`; keys are `controllerKey + methodName`.

### Decisive source
```ts
private getMetadataKey(controller: Controller, methodName: string): string {
  const ctor = controller.constructor;
  const controllerKey = ctor && (ctor[CONTROLLER_ID_KEY] || ctor.name);
  return controllerKey + methodName;      // id when present, name only as fallback
}

public assignControllerUniqueId(controller: Type<Controller>) {
  Object.defineProperty(controller, CONTROLLER_ID_KEY, {
    enumerable: false, writable: false, configurable: true,
    value: randomStringGenerator(),       // per-registration random id
  });
}
```

**Flow:** every controller registered in a Module gets an opaque random id stamped as a non-enumerable static (`CONTROLLER_ID_KEY = 'CONTROLLER_ID'`) → metadata cache lookups prefer that id → plain `ctor.name` is only a FALLBACK for controllers that never went through registration (tests construct bare instances).
**Invariant:** Two same-named classes from different files (or two registrations of one class under request scope) must not share cache entries — keying by name alone collides them and serves wrong argsLength/statusCode to another route. The id is non-enumerable so JSON dumps and Object.keys scans don't see it.
**Probe:** `packages/core/injector/module.ts:531` (id assignment); consumer exercised via router-execution-context.spec.ts metadata caching path. Direct storage spec absent — behavior pinned indirectly through RouterExecutionContext specs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "HandlerMetadataStorage getMetadataKey HANDLER_METADATA_SYMBOL", limit: 5 });
```

## Verdict
Adopt opaque-id-keyed method caches for any framework where duplicate class names are legal; adapt the stamping mechanism (WeakMap keyed by ctor works too); omit only if your registry guarantees unique names. Porting wrong: name-keyed caches produce cross-route metadata corruption that only reproduces with minified/duplicate names.
