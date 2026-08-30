<!-- capsule-v2 -->
# Read-only model facade for extensions — how do you expose a mutable registry read-only while keeping live values and core parity?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** How do you hand third-party code a stable `ctx.models` API that always reflects the live session model and resolves exactly like core selection?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/extensions/model-api.ts:createExtensionModelQuery` (:1-39 whole); direct test `test/extensibility/ext-model-query.test.ts` (:1-71 whole).
**Signature:** `createExtensionModelQuery(modelRegistry, settings, getModel: () => Model | undefined): ExtensionModelQuery` with `{ list, current, resolve, family }`.
**Data Shape:** list -> registry.getAvailable(); current -> lazy getter result; resolve(spec) -> Model | undefined; family(model) -> string token.

### Decisive source
```ts
// Build the `ctx.models` facade. `getModel` is read lazily so `current()` always
// reflects the live session model (it can change mid-session via `/model`).
current: () => getModel(),
// resolveModelRoleValue expands a role alias (`@slow`) to its full configured
// priority list and tries each pattern — the same path core selection uses — so a
// fallback model lower in the list still resolves. Plain model strings pass through.
resolve: (spec: string) => resolveModelRoleValue(spec, modelRegistry.getAvailable(), {
	settings, matchPreferences: getModelMatchPreferences(settings), }).model,
family: (model) => modelFamilyToken(model.id) || model.provider.toLowerCase(),
```
**Flow:** extension reads ctx.models.list/current/resolve/family -> no write path exists on the type (read-only by construction, not by convention); setModel capability lives in compact-handler.ts `runExtensionSetModel` which checks `getApiKey(model)` FIRST and returns false when absent — capability check before commit.
**Invariant:** (1) never snapshot the model at facade-build time — inject an accessor; (2) reuse the core resolver so alias/fallback semantics cannot drift between host and extensions; (3) family derivation falls back to provider name lowercased when no catalog token matches.
**Probe:** `test/extensibility/ext-model-query.test.ts`: `current()` flips from claude to gpt after the captured `active` variable changes (lazy-read pin); `q.resolve("anthropic/claude-opus-4-8")` returns exact model object; unknown string resolves undefined.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "createExtensionModelQuery", limit: 5 });
```

## Verdict
Adopt: accessor-injected read-only facade + shared-core resolution. Adapt: your registry/role-resolver names. Omit: catalog-specific family tokens if you have no model identity table.
