<!-- capsule-v2 -->
# Error message enrichment — how do DI failures name the exact missing dependency, its consumer, index, and module?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What context must travel with a resolution failure so the message pinpoints the fix?

## UnknownDependenciesException + UndefinedDependencyException
**Path/Symbol:** `packages/core/errors/exceptions/unknown-dependencies.exception.ts` (1-17); `packages/core/errors/messages.ts:UNKNOWN_DEPENDENCIES_MESSAGE`; thrown from `packages/core/injector/injector.ts:lookupComponent` (616-622) and `resolveSingleParam` (496-505).
**Signature:** `new UnknownDependenciesException(type, context: InjectorDependencyContext, moduleRef?: Module, metadata?: { id: string })`.
**Data Shape:** `InjectorDependencyContext = { key?, name?, index?, dependencies? }` — assembled at throw time from the resolution loop.

### Decisive source
```ts
// lookupComponent — fail FAST on self-reference before any graph walk
if (wrapper && token === name) {
  throw new UnknownDependenciesException(wrapper.name, dependencyContext, moduleRef, { id: wrapper.id });
}
// resolveSingleParam — undefined param (circular ES import) gets its own exception
throw new UndefinedDependencyException(wrapper.name, dependencyContext, moduleRef);
```
```ts
// messages.ts composes: "Nest can't resolve dependencies of the <Consumer>
// ( <deps...>, ? ). Please make sure that the argument dependency at index [N]
// is available in the <Module> context."
```

**Flow:** resolution loop carries `dependencyContext {index, dependencies}` → on failure the exception receives consumer name + full dep list + current module → message renders the positional `?` marker at the failing index.
**Invariant:** The exception is constructed with the CONSUMER's perspective (what was being built, which parameter) not the provider's; `moduleRef` is exposed as a plain `{id}` to avoid leaking the Module object. The self-token check (`token === name`) fires BEFORE parent-module traversal so the error never blames the wrong scope.
**Probe:** `packages/core/test/injector/injector.spec.ts:417` ("should throw UnknownDependenciesException when instanceWrapper is null...") and errors tests under `packages/core/test/errors/`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "UnknownDependenciesException UNKNOWN_DEPENDENCIES_MESSAGE", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt context-carrying exceptions (consumer + index + dep array + module id) raised at the earliest provable failure point; adapt message wording; omit the metadata bag. Porting wrong: throwing a bare "provider not found" after full-graph search hides whether the problem is a missing export vs circular import.
