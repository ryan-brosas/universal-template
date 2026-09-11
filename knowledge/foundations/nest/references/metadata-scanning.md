<!-- capsule-v2 -->
# Metadata scanning — how does the scanner turn decorator metadata into container records, and how do APP_* global enhancers get rewired?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What does scanning actually record (vs instantiate), and what is the token-rewrite trick for global providers?

## DependenciesScanner
**Path/Symbol:** `packages/core/scanner.ts:DependenciesScanner` (scan 84-102, scanForModules 104-182, insertProvider 455-502, addScopedEnhancersMetadata 646-666, applyApplicationProviders 668-705, calculateModulesDistance 414-433).
**Signature:** `scan(module): Promise<void>`; `scanForModules({moduleDefinition, lazy?, scope?, ctxRegistry?, overrides?}): Promise<Module[]>`.
**Data Shape:** `applicationProvidersApplyMap: { moduleKey, providerKey, type, scope? }[]` accumulates APP_GUARD/APP_PIPE/APP_INTERCEPTOR/APP_FILTER entries for a later apply phase.

### Decisive source
```ts
// module walk: depth-first with a ctxRegistry (not a Set) to skip in-progress branches
if (ctxRegistry.includes(innerModule)) continue;
const moduleRefs = await this.scanForModules({ moduleDefinition: innerModule, scope: [...scope, moduleDefinition], ctxRegistry, ... });

// undefined import = circular ES-import artifact — DISTINCT error from invalid module
if (innerModule === undefined) throw new UndefinedModuleException(moduleDefinition, index, scope);
if (!innerModule) throw new InvalidModuleException(...);

// GLOBAL ENHANCER REWIRE: rename the provider token so it can't collide,
// remember where it lives, register under the new key
const uuid = UuidFactory.get(type.toString());
const providerToken = `${type} (UUID: ${uuid})`;
this.applicationProvidersApplyMap.push({ type, moduleKey: token, providerKey, scope });
const newProvider = { ...provider, provide: providerToken, scope };
// request/transient globals go into injectables instead of providers
```

**Flow:** registerCoreModule first → DFS modules (dedup by reference registry) → per-module reflect imports/providers/controllers/exports (static + dynamic-metadata merge) → scoped-enhancer fan-out onto every controller/entry-provider → distance calc via TopologyTree skipping globals → bindGlobalScope.
**Invariant:** Distance ordering must be computed BEFORE globals are linked (scan() comments enforce this; globals already carry MAX). APP_* providers are applied only after all instances exist (`applyApplicationProviders` runs last in bootstrap).
**Probe:** `packages/core/test/scanner.spec.ts` (metadata reflection + insert paths).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "DependenciesScanner insertProvider applicationProvidersApplyMap", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-phase scan (register graph, then fill members) plus the UUID-token rewire + deferred apply map for global enhancers; adapt watermark metadata keys; omit microservice-specific reflection. Porting wrong: registering APP_* tokens verbatim collides across modules and applies them before their instances exist.
