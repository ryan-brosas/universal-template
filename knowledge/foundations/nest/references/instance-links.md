<!-- capsule-v2 -->
# Instance links — how does get()/resolve() find instances across ALL modules without re-walking the module graph per call?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the flattened-index contract and its strict/non-strict lookup semantics?

## InstanceLinksHost + AbstractInstanceResolver
**Path/Symbol:** `packages/core/injector/instance-links-host.ts:InstanceLinksHost` (14-94); `packages/core/injector/abstract-instance-resolver.ts:find` (18-40), `resolvePerContext` (42-70).
**Signature:** `get(token, options?: { moduleId?: string; each?: boolean }): InstanceLink | InstanceLink[]`.
**Data Shape:** `instanceLinks: Map<token, InstanceLink[]>` where `InstanceLink = { token, wrapperRef, collection, moduleId }` — built lazily on first access (getter in NestApplicationContext) or eagerly in ModuleRef.

### Decisive source
```ts
// one-time flattening of providers+injectables+controllers across all modules
modules.forEach(moduleRef => {
  providers.forEach((wrapper, token) => this.addLink(wrapper, token, moduleRef, 'providers'));
  injectables.forEach(...); controllers.forEach(...);
});
// no moduleId → LAST registered link wins
const instanceLink = options.moduleId
  ? instanceLinksForGivenToken.find(item => item.moduleId === options.moduleId)
  : instanceLinksForGivenToken[instanceLinksForGivenToken.length - 1];

// get() REFUSES scoped instances outright...
if (wrapperRef.scope === Scope.REQUEST || wrapperRef.scope === Scope.TRANSIENT
    || !wrapperRef.isDependencyTreeStatic()) throw new InvalidClassScopeException(typeOrToken);
// ...resolve() loads them per context instead
const instance = await this.injector.loadPerContext(ctorHost, wrapperRef.host!, collection, contextId, wrapperRef);
```

**Flow:** index built once from container state → get(): strict filters by moduleId, non-strict takes latest → static tree? return instance : throw. resolve(): same index, but scoped/transient wrappers are loaded per ContextId.
**Invariant:** The index is a SNAPSHOT — modules registered after construction (lazy loads) are not visible unless the host is rebuilt. Non-strict "last wins" mirrors registration recency; strict mode is keyed by Module.id, not name.
**Probe:** `packages/core/test/nest-application-context.spec.ts::get/resolve` (DEFAULT/REQUEST/TRANSIENT scopes at :219-:438, each:true at :499).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "InstanceLinksHost addLink resolvePerContext", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flattened token→links index with last-wins default and moduleId-strict filter; adapt rebuild timing to your container's mutability; omit InvalidClassScope nuance if you lack scopes. Porting wrong: rebuilding the index per get() call loses O(1) lookups; never rebuilding misses lazily added modules.
