<!-- capsule-v2 -->
# Container registration — how does the container register modules, providers, and controllers without duplicating or misplacing them?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What does the container-level add* API guarantee about idempotence, ordering side effects, and error timing?

## NestContainer
**Path/Symbol:** `packages/core/injector/container.ts:NestContainer` (addModule 93-128, setModule 164-186, addProvider 253-271, addController 297-309, bindGlobalScope 319-334, registerRequestProvider 357-363).
**Signature:** `addModule(metatype, scope): Promise<{ moduleRef, inserted } | undefined>`; `addProvider(provider, token, enhancerSubtype?): string | symbol | Function`.
**Data Shape:** `modules: ModulesContainer (Map<token, Module>)`; `globalModules: Set<Module>`; `dynamicModulesMetadata: Map<token, Partial<DynamicModule>>`; `internalProvidersStorage` holds the http adapter refs.

### Decisive source
```ts
const { type, dynamicMetadata, token } = await this.moduleCompiler.compile(metatype);
if (this.modules.has(token)) {
  return { moduleRef: this.modules.get(token)!, inserted: false };  // dedup by token
}
...
// global modules get MAX distance so their lifecycle hooks run FIRST
moduleRef.distance = Number.MAX_VALUE;
this.addGlobalModule(moduleRef);
```

**Flow:** compile → token-dedup check → construct `Module(type, this)` → store by token → persist dynamic metadata (recursively registering its `imports` with the SAME scope) → flag globals with `distance = Number.MAX_VALUE`.
**Invariant:** Registration order is observable: insertion into `modules` precedes dynamic-metadata expansion; globals are pinned to max distance at *registration* time, not init time. `addProvider/addInjectable/addExportedProviderOrModule/addController` all throw `UnknownModuleException` when the token is not yet registered — providers can only attach to an existing module. `registerRequestProvider` stores pre-resolved REQUEST instances on the internal core module's wrapper keyed by ContextId.
**Probe:** `packages/core/test/injector/container.spec.ts` (token dedup, provider/controller registration against known/unknown tokens).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "NestContainer addModule addProvider global module", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt token-keyed container with explicit `inserted` flag and distance-pinned globals; adapt the http-adapter storage to your host; omit the preview allowlist (`InitializeOnPreviewAllowlist`) unless porting preview mode. Porting wrong: re-registering a dynamic module twice creates duplicate instances because you keyed by class instead of compiled token.
