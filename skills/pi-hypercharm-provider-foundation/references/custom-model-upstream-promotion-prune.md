<!-- capsule-v2 -->
# Custom-model upstream-promotion prune — how do you keep a user's private override list from rotting once the vendor ships the same model?

**Source:** pi-hypercharm-provider MIT `main@4520704` (pass 4); Codebase Memory project `pi-hypercharm-provider`. **Question:** When an upstream catalog starts listing a model that previously existed only in custom-models.json, how does the sync run detect and retire the now-redundant local entry?

## Duplicate detection + file rewrite
**Path/Symbol:** `scripts/update-models.js:462-480` (prune block inside `main`); helpers `loadJson` :138-144 / `saveJson` :146-148; runtime counterpart `buildModels` custom-wins merge `index.ts:215-227` (owned by merge-precedence-model-pipeline.md).
**Signature:** inline block over `customModels: JsonModel[]` against `upstreamIds: Set<string>`; mutates the array IN PLACE after rewriting its file.
**Data Shape:** `custom-models.json` = `JsonModel[]` on disk, `[]` when absent/non-array (`Array.isArray(loadJson(...))` guard). Pruned file = same list minus ids present upstream.

### Decisive source
```js
const customModels = Array.isArray(loadJson(CUSTOM_MODELS_JSON_PATH))
  ? loadJson(CUSTOM_MODELS_JSON_PATH)
  : [];

// Check for custom models now available upstream (remove duplicates)
const upstreamIds = new Set(apiTransformed.map(m => m.id));
const duplicates = customModels.filter(m => upstreamIds.has(m.id));
if (duplicates.length > 0) {
  console.log(`\nFound ${duplicates.length} custom model(s) now available upstream:`);
  for (const dup of duplicates) console.log(`  - ${dup.id} (${dup.name})`);
  const cleaned = customModels.filter(m => !upstreamIds.has(m.id));
  saveJson(CUSTOM_MODELS_JSON_PATH, cleaned);
  console.log(`✓ Removed ${duplicates.length} duplicate(s) from custom-models.json`);
  customModels.length = 0;
  customModels.push(...cleaned);
}
```

**Flow:** build the upstream id set from the freshly transformed API list → intersect with custom ids → if any overlap, log each promoted id (id + display name), filter them out, REWRITE custom-models.json immediately, then refresh the in-memory array in place (`length = 0` + `push(...cleaned)`) so downstream README composition sees the pruned list.
**Invariant:** promotion is REMOVAL, not merging — a custom entry that reaches the official catalog is deleted rather than reconciled, because the API-owned transform is authoritative for canonical metadata. The in-place refresh is load-bearing: the later `buildModels(withDeprecatedForReadme(apiTransformed), customModels, patch)` call composes the SAME array object, so skipping the `length=0; push` step would render retired customs into the README while the file no longer contains them (file/memory divergence). Detection happens AFTER models.json is written but BEFORE README generation.
**Probe:** no upstream test — deterministic probe P-PRUNE executed this pass via `node -e`: fixture `customs=[{id:"a"},{id:"b"}]`, upstream `{a,c}` ⇒ duplicates `[a]`, cleaned `[b]`, in-place refresh yields `[b]`; zero-overlap case leaves array untouched (no rewrite, no log). Source-read pins :462-480.
**Coverage caveat:** untested upstream; custom-models.json ships empty at pin so the happy path is exercised only when users add entries.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider",
  query: "update-models buildModels custom", limit: 5 });
// → scripts.update-models.buildModels Function scripts/update-models.js 190-206 (consumer of the pruned list)
```

## Verdict
Adopt promote-then-prune lifecycle for any vendored-vs-upstream overlay list: intersect ids, log what retires, rewrite the overlay file, refresh the shared in-memory array before composing derived views. Adapt id semantics to your domain. Omit the hypercharm-specific logging strings.
