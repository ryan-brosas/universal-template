<!-- capsule-v2 -->
# ModuleRef.create + introspect — how does user code instantiate ad-hoc classes inside the container, and ask for a provider's scope?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How does an out-of-band class get full DI treatment without being registered, and how is scope exposed?

## ModuleRef.instantiateClass / introspect
**Path/Symbol:** `packages/core/injector/module-ref.ts:instantiateClass` (163-216), `introspect` (145-157); per-module subclass overrides in `module.ts:createModuleReferenceType` (613-665).
**Signature:** `create<T>(type: Type<T>, contextId?: ContextId): Promise<T>`; `introspect(token): { scope: Scope }`.
**Data Shape:** creates a THROWAWAY InstanceWrapper (never inserted into module collections) seeded with a prototype shell under the target context.

### Decisive source
```ts
const wrapper = new InstanceWrapper({
  name: type?.name, metatype: type, isResolved: false,
  scope: getClassScope(type), durable: isDurable(type), host: moduleRef,
});
if (type?.prototype) {
  wrapper.setInstanceByContextId(contextId ?? STATIC_CONTEXT, {
    instance: Object.create(type.prototype),   // shell FIRST, like forwardRef handling
    isResolved: false, isPending: false,
  });
}
...
const instance = new type(...instances);        // real construction after deps resolve
this.injector.applyProperties(instance, properties);
resolve(instance);
```
```ts
// scope introspection — tree staticity wins over declared transient flag
let scope = Scope.DEFAULT;
if (!wrapperRef.isDependencyTreeStatic())      scope = Scope.REQUEST;
else if (wrapperRef.isTransient)               scope = Scope.TRANSIENT;
```

**Flow:** create() → build ephemeral wrapper in the CALLING module → standard resolveConstructorParams/resolveProperties with `inquirer: wrapper` → construct + property-inject → resolve promise. Errors reject via `.catch(reject)` on the loader chain.
**Invariant:** The wrapper is NOT stored in any module map — repeated create() calls produce independent instances even for DEFAULT-scope classes. Introspection derives REQUEST from tree staticity, not from the declared scope, because a DEFAULT provider consuming request-scoped deps is effectively request-scoped.
**Probe:** `packages/core/test/injector/module-ref.spec.ts` + `packages/core/test/scope/transient-scope.spec.ts::creating an instance with moduleRef.create`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ModuleRef instantiateClass introspect createModuleReferenceType", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ephemeral-wrapper instantiation for container-backed construction of unregistered classes and tree-derived scope introspection; adapt to your resolver's entry API; omit InvalidClassException wrapping. Porting wrong: caching created instances on the host module silently converts per-call semantics into singletons.
