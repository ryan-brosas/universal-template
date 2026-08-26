<!-- capsule-v2 -->
# Config normalization plane — how does multi-account config stay entry-stable across corrupt files and env overlays?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** How can a multi-account routing config be loaded from disk plus env, merged, and re-saved without corrupting partial files or renumbering surviving accounts?

## Normalization + merge keeps account identity stable
**Path/Symbol:** `extensions/multi-sub.ts`: `normalizeMultiPassConfig` (1585-1593), `loadGlobalConfig` (1604-1613), `mergeConfigs` (1806-1821), `normalizeEntries` (1823-1846), `subProviderName` (1852-1854).
**Signature:** `function normalizeMultiPassConfig(raw: unknown): MultiPassConfig`; `function mergeConfigs(fileConfig: MultiPassConfig, envEntries: SubEntry[]): SubEntry[]`; `function normalizeEntries(entries: SubEntry[]): SubEntry[]`; `function subProviderName(entry: SubEntry): string`.
**Data Shape:** MultiPassConfig = {subscriptions: SubEntry[], pools, chains, presets}; SubEntry = {provider: string, index: number, label?}. Identity is the derived name `${provider}-${index}` (index 1 renders as bare provider via callers). Env entries come from `MULTI_SUB="provider:count,..."`.

### Decisive source
```ts
function normalizeEntries(entries: SubEntry[]): SubEntry[] {
	const byProvider = new Map<string, SubEntry[]>();
	for (const entry of entries) {
		const list = byProvider.get(entry.provider) || [];
		list.push(entry);
		byProvider.set(entry.provider, list);
	}
	const result: SubEntry[] = [];
	for (const [, list] of byProvider) {
		const usedIndices = new Set(list.filter((e) => e.index > 0).map((e) => e.index));
		let nextIndex = 2;
		for (const entry of list) {
			if (entry.index > 0) {
				result.push(entry);
			} else {
				while (usedIndices.has(nextIndex)) nextIndex++;
				result.push({ ...entry, index: nextIndex });
				usedIndices.add(nextIndex);
				nextIndex++;
			}
		}
	}
	return result;
}
```

**Flow:** read raw JSON -> normalizeMultiPassConfig coerces every missing/non-array section to [] (never throws) -> loadGlobalConfig catches JSON parse errors and returns an EMPTY config rather than crashing -> mergeConfigs appends only env entries whose provider count exceeds what the file already has, assigning lowest unused index >= 2 -> normalizeEntries groups by provider and fills index-0 placeholders with the lowest free index >= 2, keeping explicit indices untouched.
**Invariant:** explicit indices are never renumbered; index 1 is implicit (the base subscription); new accounts always take the LOWEST FREE index >= 2 so a stable `${provider}-${index}` identity survives add/remove cycles and file+env merges; a malformed config file degrades to empty, never to a crash.
**Probe:** `node tests/subs-switch-check.mjs` and `node tests/project-restriction-check.mjs` (both replicate normalizeEntries/mergeConfigs/subProviderName and pin identity + restriction behavior; all green at b9d9d1d7a092).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "normalizeEntries mergeConfigs subProviderName", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt defensive normalization (never throw on user-edited config), derived `${provider}-${index}` identity, and lowest-free-index fill. Adapt the storage paths (~/.pi/agent/multi-pass.json) to your host's config dir and the MULTI_SUB env grammar to your CLI surface. Omit pi-specific PROVIDER_TEMPLATES display logic.