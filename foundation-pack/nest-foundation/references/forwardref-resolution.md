<!-- capsule-v2 -->
# forwardRef resolution — how do circular imports still resolve, and why does the instance get Object.assign-merged?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the exact contract when a dependency token arrives as a ForwardReference or the wrapper was created before its target existed?

## resolveParamToken / resolveComponentHost / instantiateClass
**Path/Symbol:** `packages/core/injector/injector.ts:resolveParamToken` (517-526), `resolveComponentHost` (549-603), `instantiateClass` (845-884).
**Signature:** `resolveParamToken(wrapper, param): InjectionToken`; `resolveComponentHost(moduleRef, instanceWrapper, resolutionContext?): Promise<InstanceWrapper>`.
**Data Shape:** `ForwardReference = { forwardRef: () => Type }`; `wrapper.forwardRef?: boolean` latches once any param used one.

### Decisive source
```ts
// unwrap the thunk AND latch the flag on the wrapper
if (typeof param === 'object' && 'forwardRef' in param) {
  wrapper.forwardRef = true;
  return param.forwardRef();
}

// resolveComponentHost — forwardRef + not yet resolved:
//   DON'T load now; merge later when the deferred load finishes
instanceHost.donePromise && void instanceHost.donePromise
  .then(() => this.loadProvider(instanceWrapper, moduleRef, resolutionContext))
  .catch(err => { instanceWrapper.settlementSignal?.error(err); });

// instantiateClass — the prototype shell already exists (from cloneStaticInstance);
// assign real fields ONTO it instead of replacing the object identity
instanceHost.instance = wrapper.forwardRef
  ? Object.assign(instanceHost.instance, new (metatype)(...instances))
  : new (metatype)(...instances);
```

**Flow:** param is `{forwardRef}` → call thunk for the type, mark wrapper → host lookup sees unresolved+forwardRef → returns early, scheduling completion off `donePromise` → when both sides finish, late constructor output is merged into the existing prototype shell so earlier-captured references stay valid.
**Invariant:** The prototype shell must be created (Object.create) BEFORE construction so circular partners can hold a reference; identity is preserved and fields merged. `isResolved` checks throughout skip loading when either side already finished (`!instanceHost.isResolved && !paramWrapperWithInstance.forwardRef` guards staticity marking).
**Probe:** `packages/core/test/injector/injector.spec.ts::resolveComponentHost` ("should not call loadProvider (forwardRef)" :653; forward-ref non-static branch :684) + `::resolveParamToken`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "forwardRef resolveComponentHost donePromise Object.assign", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt thunk-unwrapping + deferred-load + in-place prototype merge as THE circular-import strategy; adapt to your language's object model if identity semantics differ; omit request-scoped lazy-merge special casing when scopes are absent. Porting wrong: constructing normally into a fresh object breaks every reference taken before the cycle closed.
