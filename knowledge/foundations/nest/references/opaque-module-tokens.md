<!-- capsule-v2 -->
# Opaque module tokens — how are module instances deduplicated when the same class or dynamic module appears many times?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What identity does a module carry in the container, and what breaks if a porter substitutes class identity for token identity?

## ModuleCompiler + ByReferenceModuleOpaqueKeyFactory
**Path/Symbol:** `packages/core/injector/compiler.ts:ModuleCompiler.compile` (+ `extractMetadata`, `isDynamicModule`); `packages/core/injector/opaque-key-factory/by-reference-module-opaque-key-factory.ts:getOrCreateModuleId`.
**Signature:** `compile(moduleClsOrDynamic: Type | DynamicModule | ForwardReference | Promise<DynamicModule>): Promise<ModuleFactory>` where `ModuleFactory = { type, token, dynamicMetadata? }`.
**Data Shape:** Input may be a promise (awaited first), a forward reference (`{ forwardRef: () => Type }`), a plain class, or a DynamicModule `{ module, ...metadata }`. Output token is an opaque random string (or `"rand:sha256(...)"` under `snapshot`/deep-hash mode), cached on the original object under symbol `K_MODULE_ID`.

### Decisive source
```ts
// compiler.ts
moduleClsOrDynamic = await moduleClsOrDynamic;
const { type, dynamicMetadata } = this.extractMetadata(moduleClsOrDynamic);
const token = dynamicMetadata
  ? this._moduleOpaqueKeyFactory.createForDynamic(type, dynamicMetadata, ...)
  : this._moduleOpaqueKeyFactory.createForStatic(type, ...);

// by-reference factory — cache the id ON THE ORIGINAL REFERENCE
if (originalRef[K_MODULE_ID]) return originalRef[K_MODULE_ID];
...
originalRef[K_MODULE_ID] = moduleId;
```

**Flow:** await input → extract `{type, metadata}` (unwrap forwardRef by calling it; split DynamicModule's `module` key out) → create-or-fetch opaque token via symbol-cached factory → return triple.
**Invariant:** Two evaluations of the *same object reference* must yield the SAME token (that is the dedup key `NestContainer.addModule` checks via `this.modules.has(token)`). The cache lives on the passed reference, NOT on the class — so `forRoot()` producing fresh object literals each call intentionally yields distinct tokens (distinct configured instances), while one literal reused twice collapses to one module.
**Probe:** `packages/core/test/injector/compiler.spec.ts` (token stability across repeated compile of same/dynamic inputs).
**Coverage caveat:** none recorded (check_index_coverage no_recorded_issue/metadata_match).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ModuleCompiler compile opaque key", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the symbol-cached-by-reference opaque token + `{type, token, metadata}` compile result as the container dedup primitive; adapt key generation strategy (random vs content-hash) to your snapshot/reproducibility needs; omit Nest-specific metadata keys. Porting wrong: keying modules by class alone silently merges distinct `register()` configurations.
