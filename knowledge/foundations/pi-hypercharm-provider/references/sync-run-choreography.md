<!-- capsule-v2 -->
# Sync-run choreography — what does an offline catalog-sync run actually do, in what order, and how does it fail?

**Source:** pi-hypercharm-provider MIT `main@4520704` (pass 4); Codebase Memory project `pi-hypercharm-provider`. **Question:** When the update script runs end-to-end, which files are written in which order, what fails loudly vs silently, and can you trust its "preserving existing curated data" comment?

## scripts/update-models.js main()
**Path/Symbol:** `scripts/update-models.js:407-527` (`main`, invoked unconditionally at :529); key resolution `resolveApiKey()` :116-128 (owned by config-value-resolution.md); graveyard step owned by deprecated-model-graveyard.md; prune step owned by custom-model-upstream-promotion-prune.md.
**Signature:** `async function main(): Promise<void>` — exits via `process.exit(1)` on any failure.
**Data Shape:** reads auth.json + `/v1/provider`; writes `models.json` (wholesale), maybe `deprecated-models.json`, maybe `custom-models.json`, then `README.md`. No atomic renames anywhere.

### Decisive source
```js
const apiKey = resolveApiKey();
if (!apiKey) { console.error('Error: No API key found: ...'); process.exit(1); }   // LOUD, pre-flight
...
const response = await fetch(MODELS_API_URL, { headers: { Authorization: `Bearer ${apiKey}` } });
if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);  // LOUD w/ status
const apiModels = Array.isArray(apiResponse) ? apiResponse : (apiResponse.models || apiResponse.data || []);
if (!Array.isArray(apiModels)) throw new Error('API response does not contain an array of models');
...
// Load existing models.json — source of truth for curated specs
let existingModels = []; /* read old file, [] on error */
const existingModelsMap = {};            // built...
for (const m of existingModels) existingModelsMap[m.id] = m;
// Transform models from API, preserving existing curated data   ← comment lies
let apiTransformed = apiModels.map(m => transformModel(m));
apiTransformed.sort((a, b) => a.name.localeCompare(b.name));
updateDeprecatedModels(MODELS_JSON_PATH, apiTransformed);          // BEFORE overwrite (reads old file itself)
fs.writeFileSync(MODELS_JSON_PATH, JSON.stringify(apiTransformed, null, 2) + '\n');  // wholesale replace
```
The summary diff uses the ARRAY, never the map: `existingModels.find(m => m.id === model.id)` (:506).

**Flow:** pre-flight key gate (exit 1 with usage hint naming both sources) → fetch (non-2xx ⇒ throw with HTTP status; body shape tolerated as array | `{models}` | `{data}`, else throw) → reconcile graveyard against fresh list BEFORE overwriting models.json → write models.json WHOLESALE from transformed API data → prune promoted customs from custom-models.json → build README view (`withDeprecatedForReadme(apiTransformed)` + patch + customs), sort by name → rewrite README table + model count → print summary: totals, new/removed ids (array-vs-array diff), pricing changes per id.
**Invariant:** this script is the LOUD twin of the runtime's null-ladders — a human must notice a failed sync, so every failure exits non-zero instead of degrading. Write order matters: graveyard reconcile MUST precede the models.json overwrite because it re-reads the OLD file itself (call-site comment :455-457). models.json content is exactly `transformModel` output sorted by `name.localeCompare` — curated specs do NOT survive from the old file; `existingModelsMap` is DEAD CODE (built :443-446, zero reads at pin `4520704`) and the "preserving existing curated data" comment describes intent the code dropped when the catalog became fully API-owned. A porter who trusts that comment and merges old entries will diverge from upstream output.
**Probe:** no upstream test for the script — deterministic probes executed this pass: `node --check scripts/update-models.js` exit 0 (P-CHOREO-SYN); call-site census `grep -c convertPricing|existingModelsMap` proving zero uses beyond their definitions (P-DEAD, see also research.md findings). Source-read pins :407-529.
**Coverage caveat:** script untested upstream; JSON outputs double as snapshot fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-hypercharm-provider",
  qualified_name: "pi-hypercharm-provider.scripts.update-models.main" });
// → Function scripts/update-models.js 407-527, callers:1 (module tail), callees:8
```

## Verdict
Adopt the loud-fail CLI posture, response-shape tolerance ladder, and write ordering. Adapt endpoints and file paths. Omit the README-generation tail (standing boundary) and NEVER re-introduce map-based curation merge — upstream deliberately overwrites.
