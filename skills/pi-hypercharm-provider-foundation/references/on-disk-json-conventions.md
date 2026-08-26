<!-- capsule-v2 -->
# On-disk JSON conventions — how do corrupt or missing JSON files degrade across the script and runtime twins?

**Source:** pi-hypercharm-provider MIT `main@4520704` (pass 4); Codebase Memory project `pi-hypercharm-provider`. **Question:** Every surface in this repo reads and writes small JSON files (cache, config, catalogs, graveyard) — what is the uniform on-disk contract, and which writers fail soft vs loud?

## loadJson / saveJson vs runtime write sites
**Path/Symbol:** `scripts/update-models.js:138-148` (`loadJson`, `saveJson`); runtime twins `index.ts:318-325` (`loadCachedModels` → null), `index.ts:327-334` (`cacheModels` → silent), `index.ts:433-441` (`loadStatusConfig` → defaults), `index.ts:443-461` (`writeStatusConfig` → silent).
**Signature:** `loadJson(filePath): any` (`{}` on ANY failure); `saveJson(filePath, data): void` (throws).
**Data Shape:** every persisted artifact is `JSON.stringify(x, null, 2) + "\n"` — two-space indent, single trailing newline, no atomic rename.

### Decisive source
```js
// script side: reads fail SOFT to {}, writes are LOUD
function loadJson(filePath) {
  try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); }
  catch { return {}; }
}
function saveJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2) + '\n');   // throws
}
```
```ts
// runtime side: BOTH directions fail soft
function cacheModels(models: JsonModel[]): void {
	try {
		fs.mkdirSync(CACHE_DIR, { recursive: true });
		fs.writeFileSync(CACHE_PATH, JSON.stringify(models, null, 2) + "\n");
	} catch {
		// Cache write failure is non-fatal
	}
}
```
(reads: `loadCachedModels` try/catch→null; `loadStatusConfig` try/catch→in-memory defaults; `writeStatusConfig` re-reads foreign JSON into `raw` and preserves unknown keys before overwriting its own four.)

**Flow:** script path: patch.json read via `loadJson` ⇒ a CORRUPT patch silently degrades to "no overrides" (`{}` matches the `PatchData` record shape; empty object = no-op), while models/custom/README writes propagate exceptions to main()'s exit(1). Runtime path: cache/config reads AND writes are all wrapped — a missing/unreadable file means defaults or stale-embedded service, never an extension error.
**Invariant:** formatting is uniform everywhere (2-space + `\n`) so git diffs of committed artifacts (models.json, deprecated-models.json, hypercharm.json) stay line-stable. The asymmetry is deliberate posture, not oversight: the offline SCRIPT must be loud (a human runs it once and must notice failures — see sync-run-choreography.md), while RUNTIME paths inside a live editor session must never crash pi over telemetry-grade files. Note the type-level subtlety: `loadJson`'s `{}` fallback only type-checks for RECORD-shaped consumers (patch.json); list-shaped consumers MUST add their own `Array.isArray` guard (the custom-models load does; forgetting it turns corruption into `.filter is not a function`).
**Probe:** no upstream test — deterministic probe P-JSON executed this pass via `node -e`: replicated loadJson semantics against a missing path (returned `{}`), and saveJson formatting assertion `JSON.stringify({a:1}, null, 2)+"\n" === '{\n  "a": 1\n}\n'`. Source-read pins :138-148, :318-334, :443-461.
**Coverage caveat:** untested upstream; runtime paths verified by source-read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "pi-hypercharm-provider",
  qualified_name: "pi-hypercharm-provider.scripts.update-models.loadJson" });
// → Function scripts/update-models.js 138-144
```

## Verdict
Adopt the split posture (script loud / runtime fail-soft), the uniform 2-space+newline serializer, and per-shape degradation guards. Adapt paths and failure notifications. Omit nothing else — this is the whole contract.
