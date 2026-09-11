<!-- capsule-v2 -->
# Module overrides — how can a test or host swap a module implementation BEFORE any registration happens?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the override matching rule, and how does replacement preserve token identity?

## DependenciesScanner.insertOrOverrideModule + NestContainer.replaceModule
**Path/Symbol:** `packages/core/scanner.ts:insertOrOverrideModule` (553-577), `getOverrideModuleByModule` (579-597), `overrideModule` (599-617); `container.ts:replaceModule` (130-162).
**Signature:** `overrides?: ModuleOverride[]` threaded through scanForModules; `replaceModule(metatypeToReplace, newMetatype, scope)`.
**Data Shape:** `ModuleOverride = { moduleToReplace: Type | ForwardReference, newModule: Type | DynamicModule }`.

### Decisive source
```ts
// match by REFERENCE, including through forwardRef thunks
if (this.isForwardReference(module)) {
  return overrides.find(o =>
    o.moduleToReplace === module.forwardRef() ||
    (o.moduleToReplace as ForwardReference).forwardRef?.() === module.forwardRef());
}
return overrides.find(o => o.moduleToReplace === module);

// replaceModule — compiles the OLD module ONLY to steal its token,
// then registers the new type under that same token
const { token } = await this.moduleCompiler.compile(metatypeToReplace);
const { type, dynamicMetadata } = await this.moduleCompiler.compile(newMetatype);
return { moduleRef: await this.setModule({ token, type, dynamicMetadata }, scope), inserted: true };
```

**Flow:** every module insert checks the override list first → on match, old module compiled for token capture → new metatype stored under the old token → importers referencing the original class resolve to the replacement.
**Invariant:** Token preservation is the whole mechanism — replace does NOT rewrite importers. The old module's own providers never register (setModule overwrites the map entry). Matching is reference-based; string/positional matching would break DynamicModules.
**Probe:** `packages/core/test/scanner.spec.ts` (override branches) + `packages/core/test/injector/container.spec.ts::replaceModule`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "replaceModule moduleOverrides insertOrOverrideModule", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pre-registration override matching with token-carryover replacement; adapt to your test harness's swap points; omit forwardRef double-thunk handling if you lack forward references. Porting wrong: registering the replacement as a NEW token strands importers on the original (never-instantiated) module.
