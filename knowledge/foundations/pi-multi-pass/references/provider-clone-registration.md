<!-- capsule-v2 -->
# Provider clone registration — how do N accounts of one base provider become distinct registered providers without duplicating credentials or model catalogs?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** When a user adds a second account of a provider they already use, how do you register it as a first-class provider — its own OAuth identity and its own model list — while sharing the base implementation?

## Template-parameterized OAuth + deep-cloned model catalog under a derived name
**Path/Symbol:** `extensions/multi-sub.ts`: `registerSub` (1898-1915), `cloneModels` (1877-1892), `ProviderTemplate.buildOAuth(index)` (e.g. Antigravity template 217-238), `handleSubsAdd` (3063-3119); identity helpers `subProviderName`/`getBaseProvider` (1852-1871).
**Signature:** `function registerSub(pi: ExtensionAPI, entry: SubEntry): void`; `function cloneModels(originalProvider: string, index: number)`; `buildOAuth(index: number): OAuthConfig`.
**Data Shape:** SubEntry = {provider, index, label?}; registered name = `${provider}-${index}` (index 1 renders bare); each template supplies `buildOAuth(index)` so every clone gets an independently-named OAuth flow (`Antigravity #2`, distinct display name in the login picker) but the SAME login/refresh/getApiKey implementation.

### Decisive source
```ts
function registerSub(pi: ExtensionAPI, entry: SubEntry): void {
	const template = PROVIDER_TEMPLATES[entry.provider];
	if (!template) return;
	const name = subProviderName(entry);
	const oauth = template.buildOAuth(entry.index);          // per-index identity, shared logic
	const modifyModels = template.buildModifyModels?.(name);
	const builtinModels = getModels(entry.provider as any) as Model<Api>[];
	const baseUrl = builtinModels[0]?.baseUrl || "";
	const models = cloneModels(entry.provider, entry.index);
	pi.registerProvider(name, { baseUrl, api: builtinModels[0]?.api,
		oauth: modifyModels ? { ...oauth, modifyModels } : oauth, models });
}
// cloneModels: fresh objects per clone; display name suffixed; nested maps COPIED not shared
return models.map((m) => ({
	id: m.id, name: `${m.name} (#${index})`, api: m.api, reasoning: m.reasoning,
	thinkingLevelMap: m.thinkingLevelMap ? { ...m.thinkingLevelMap } : undefined,
	input: m.input as ("text" | "image")[], cost: { ...m.cost },
	contextWindow: m.contextWindow, maxTokens: m.maxTokens,
	headers: m.headers ? { ...m.headers } : undefined, compat: m.compat,
}));
```

**Flow:** `/subs add` -> pick a SUPPORTED provider (template lookup rejects unknown names before any state changes) -> optional label -> load+merge+normalize existing entries and take the LOWEST FREE index >= 2 for that base (same allocation rule as the config plane) -> push entry + saveGlobalConfig FIRST, then registerSub + modelRegistry.refresh -> offer immediate login. Registration derives the clone name, builds index-specific OAuth via the template factory, clones the full model catalog with per-clone display names (`(#2)`) and defensively copied nested structures (cost, headers, thinkingLevelMap), then registers baseUrl/api from the base's first built-in model.
**Invariant:** one template, many clones — clone behavior is inherited from the base template while identity (name, OAuth display name, model display suffix) is parameterized by index; config persistence happens BEFORE registry registration so a crash cannot leave an unregistered-but-saved or registered-but-unsaved split that later passes would re-register differently; cloned model objects never share mutable nested references with the base catalog.
**Probe:** `node tests/subs-switch-check.mjs` (its twin pins `subProviderName` identity and resolution of models UNDER the clone name `openai-codex-2`, including base-fallback when a preferred id is missing; green at b9d9d1d7a092). COVERAGE CAVEAT: no check script imports cloneModels/registerSub directly (the harness stubs providers); these functions were verified by direct source reads at the pin only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "registerSub cloneModels handleSubsAdd buildOAuth", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt template-parameterized cloning: derive the account name from provider+index, factory-build per-account OAuth from one shared implementation, deep-clone the model catalog with suffixed display names and copied nested maps, and persist config before registering with the host. Adapt PROVIDER_TEMPLATES/buildOAuth to your host's provider-plugin surface. Omit pi's getModels global registry and the TUI select/input wrappers.
