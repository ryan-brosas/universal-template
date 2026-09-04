<!-- capsule-v2 -->
# Instance wrapper — how does one provider definition serve singleton, per-request, and per-inquirer instances at once?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the exact keying of the instance caches, and when does a read clone a new pending entry?

## InstanceWrapper
**Path/Symbol:** `packages/core/injector/instance-wrapper.ts:InstanceWrapper` (values 89, transientMap 92-94, getInstanceByContextId 146-163, getInstanceByInquirerId 165-178, cloneStaticInstance 349-365, getStaticTransientInstances 482-495).
**Signature:** `getInstanceByContextId(contextId: ContextId, inquirerId?: string): InstancePerContext<T>`; `setInstanceByContextId(contextId, value, inquirerId?)`.
**Data Shape:** `InstancePerContext = { instance, isResolved?, isPending?, donePromise?, isConstructorCalled? }`. Default-scope instances: `WeakMap<ContextId, InstancePerContext>`. TRANSIENT scope: `Map<inquirerId, WeakMap<ContextId, InstancePerContext>>` (allocated only in `initialize` when scope is transient).

### Decisive source
```ts
public getInstanceByContextId(contextId, inquirerId?) {
  if (this.scope === Scope.TRANSIENT && inquirerId) {
    return this.getInstanceByInquirerId(contextId, inquirerId);  // two-level key
  }
  const instancePerContext = this.values.get(contextId);
  return instancePerContext
    ? instancePerContext
    : contextId !== STATIC_CONTEXT
      ? this.cloneStaticInstance(contextId)   // lazily clone per request context
      : { instance: null, isResolved: true, isPending: false };
}
// clone only materializes a bare prototype shell; the constructor runs later
if (this.isNewable()) instancePerContext.instance = Object.create(this.metatype!.prototype);
```

**Flow:** lookup → transient? route to inquirer-keyed map : context-keyed map → miss outside static context ⇒ clone static entry with `isResolved:false` + prototype-shell instance → caller later loads it and sets the real instance.
**Invariant:** A missing STATIC_CONTEXT entry returns `{instance:null, isResolved:true}` — the static slot is authoritative even when empty. Cloned entries are pending until `Injector.loadInstance` completes them. Lifecycle-hook iteration must use `getStaticTransientInstances()`, which filters on `isConstructorCalled` so hooks never fire on prototype shells.
**Probe:** `packages/core/test/injector/instance-wrapper.spec.ts` (tree-static/durable introspection incl. circular refs) + `packages/core/test/scope/transient-scope.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "InstanceWrapper getInstanceByContextId cloneStaticInstance transientMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-keyed instance cache (context × inquirer for transients, lazy prototype-shell clones); adapt ContextId payload plumbing; omit the WeakMap parent registry if you don't need cache invalidation. Porting wrong: storing transient instances in one flat map makes different parents share one instance — exactly what `nested-transient-isolation.spec.ts` guards against.
