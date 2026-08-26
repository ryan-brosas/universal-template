<!-- capsule-v2 -->
# Options Storage & Feature Renames — how does per-domain config stay backward-compatible across hundreds of renamed features?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** How are defaults derived from the feature list itself, and what migration ladder preserves user settings through renames?

## Connected graph-selected seam
**Path/Symbol:** `source/options-storage.ts` (:1–61 incl. defaults :228–235 of combined listing, `isFeatureDisabled` :237–241, migrations :243–265, `getToken` :273–276); renames data `source/feature-renames.json`; id derivation `source/feature-data.ts:getNewFeatureName`.
**Signature:** `defaults = Object.assign({actionUrl, customCss, personalToken, logging, logHttp}, Object.fromEntries(importedFeatures.map(id => [\`feature:${id}\`, id !== 'extensible-nav'])))`.
**Data Shape:** options keys are `feature:<id>` booleans plus five global settings. Storage is PER-DOMAIN (`OptionsSyncPerDomain`) so github.com and a GHE host keep independent configs.

### Decisive source
```ts
export function isFeatureDisabled(options: RghOptions, id: string): boolean {
	// Must check if it's specifically `false`: It could be undefined if not yet in
	// the readme or if misread from the entry point (#6606)
	return options[`feature:${id}`] === false;
}
```
```ts
const migrations = [
	(options) => {                       // rename carrier: copy old key → new key, keep boolean
		for (const [from, to] of Object.entries(renamedFeatures)) {
			if (typeof options[`feature:${from}`] === 'boolean') {
				options[`feature:${to}`] = options[`feature:${from}`];
			}
		}
	},
	(options) => { /* logHTTP→logHttp, customCSS→customCss case fixes */ },
	OptionsSyncPerDomain.migrations.removeUnused,   // dropped features' keys get GC'd
];
```

**Flow:** every feature contributes its own default by existing in `importedFeatures` (opt-out model, one opt-IN exception) → read path goes through per-domain sync storage → migrations run oldest-first on load: rename-carrier, case-fix, remove-unused.
**Invariant:** disabled-check MUST be strict `=== false` — treating undefined as enabled-vs-disabled flips features when the key hasn't synced yet (#6606). Rename migration copies ONLY genuine booleans so an unset old key doesn't manufacture a default for the new one. `getToken` reads a PROMISE CACHED AT MODULE LOAD (`cachedSettings = optionsStorage.getAll()` captured once) — token changes require a page reload to take effect; porters adding live-token updates break this assumption silently.
**Probe:** `source/feature-renames.test.ts` pins rename-map integrity (every `from` was a real past feature id); `hotfix-parse.test.ts` covers the adjacent version logic. Migration ordering is source-cited (:243–265).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "options-storage isFeatureDisabled migrations importedFeatures", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: derive defaults from the registry, strict-false disable checks, JSON-driven rename migrations with remove-unused tail, per-domain isolation. Adapt key prefixes and storage backend. Omit GHE-specific domain handling if single-origin. Partial direct tests (renames) — caveat recorded for migrations.
