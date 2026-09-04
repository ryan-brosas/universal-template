<!-- capsule-v2 -->
# Merge precedence: base → patch → custom — in what order do model overrides compose, and which source wins each field?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** When embedded catalog, patch.json corrections, custom-models.json additions, live API data, AND grace-period deprecated models all define the same model id, who wins — field by field?

## buildModels + applyPatch + withDeprecated
**Path/Symbol:** `index.ts:162-196` (`applyPatch` :162, per-field merge + sanitation), `index.ts:198-232` (`buildModels` :198), `index.ts:371-392` (`DEPRECATED_MODEL_TTL_MS` :371/`activeDeprecatedModels` :374-388/`withDeprecated` :389-393), `index.ts:336-369` (`mergeWithEmbedded`). Duplicated for offline README builds at `scripts/update-models.js:159-222`.
**Signature:** `buildModels(base: JsonModel[], custom: JsonModel[], patch: PatchData): JsonModel[]`; `applyPatch(model: JsonModel, patch: PatchEntry): JsonModel`; `withDeprecated(models: JsonModel[]): JsonModel[]`.
**Data Shape:** `PatchData = Record<string, PatchEntry>` keyed by model id; `PatchEntry` fields are ALL optional (partial override). Result keyed uniquely by id via `Map`.

### Decisive source
```ts
function buildModels(base: JsonModel[], custom: JsonModel[], patch: PatchData): JsonModel[] {
	const modelMap = new Map<string, JsonModel>();
	// Seed with the base list plus grace-period deprecated models so patch.json
	// entries apply to deprecated models exactly as while the model was live
	for (const model of withDeprecated(base)) {
		modelMap.set(model.id, model);
	}
	for (const [id, patchEntry] of Object.entries(patch)) {
		const existing = modelMap.get(id);
		if (existing) {
			modelMap.set(id, applyPatch(existing, patchEntry));
		}
	}
	for (const model of custom) {
		const existing = modelMap.get(model.id);
		const patchEntry = patch[model.id];
		if (existing && patchEntry)      modelMap.set(model.id, applyPatch(model, patchEntry));
		else if (existing)               modelMap.set(model.id, model);   // custom REPLACES base wholesale
		else if (patchEntry)             modelMap.set(model.id, applyPatch(model, patchEntry));
		else                             modelMap.set(model.id, model);
	}
	return Array.from(modelMap.values());
}
```

**Flow:** seed map with `withDeprecated(base)` → apply every patch entry that matches an existing id (patches never CREATE models) → insert customs last, where a custom colliding with a base id REPLACES the base entry entirely (then gets its own patch applied).
**Invariant:** precedence per field is **custom > patch > base**, EXCEPT cost/contextWindow after a live merge (`mergeWithEmbedded`, `index.ts:344-352`: `{...liveModel, ...embedded, cost: liveModel.cost, contextWindow: liveModel.contextWindow || embedded.contextWindow}` — "the official catalog is authoritative for pricing, including legitimately zero-priced preview models" while curation wins via `...embedded`). `applyPatch` itself does per-FIELD merges: `cost` subfields fall back one-by-one (`?? result.cost.input`), `compat` shallow-merges over the old object. Post-patch sanitation is the porting trap: a non-reasoning model has `thinkingFormat` DELETED from compat, its whole `thinkingLevelMap` deleted, and an emptied compat object removed entirely (`index.ts:184-192`) — a porter who skips this ships broken thinking params to non-reasoning models.
**Probe:** no dedicated test file for index.ts pipeline — deterministic probe: run `node -e` importing nothing but replicating the three delete rules against a fixture; upstream coverage gap recorded. The twin copy in scripts/update-models.js keeps README rendering consistent with runtime behavior.
**Coverage caveat:** runtime merge path untested upstream; smoke suite covers only status.ts.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "buildModels", limit: 5 });
// → pi-hypercharm-provider.buildModels Function index.ts 193-225 (+ scripts twin)
```

## Verdict
Adopt the three-stage composition and the post-patch sanitation deletes verbatim. Adapt source files/paths to your provider. Omit Charm-specific pricing-authority commentary if your API owns no pricing.
