<!-- capsule-v2 -->
# Cache-pricing field remap — which API price lands in cacheRead vs cacheWrite, and why did the mapping invert?

**Source:** pi-hypercharm-provider MIT `main@4520704` (commit `49f661b` "correct cache pricing mapping to match official provider"); Codebase Memory project `pi-hypercharm-provider`. **Question:** The Charm catalog ships `cost_per_1m_in_cached` and `cost_per_1m_out_cached` but the host model record has `cacheRead`/`cacheWrite` — what is the correct projection, and what does the pre-49f661b mapping get wrong?

## Cached-output ⇒ cacheRead, cached-input ⇒ cacheWrite
**Path/Symbol:** runtime transform `index.ts:285-290` inside `transformApiModel` `index.ts:266-300`; script twin `scripts/update-models.js:255-262` inside `transformModel` `:238-274`.
**Signature:** pure field projection inside the catalog→JsonModel cost block; both twins must stay in lockstep.
**Data Shape:** Charm API: `cost_per_1m_in`, `cost_per_1m_out`, `cost_per_1m_in_cached` (discounted repeated-input tokens), `cost_per_1m_out_cached`. Host JsonModel cost: `{input, output, cacheRead, cacheWrite}`.

### Decisive source
```ts
// index.ts (runtime twin)
cost: {
	input:     apiModel.cost_per_1m_in || 0,
	output:    apiModel.cost_per_1m_out || 0,
	cacheRead: apiModel.cost_per_1m_out_cached || 0,
	cacheWrite: apiModel.cost_per_1m_in_cached || 0,
},
```
```js
// scripts/update-models.js (script twin)
cacheRead: typeof apiModel.cost_per_1m_out_cached === 'number' ? apiModel.cost_per_1m_out_cached : 0,
cacheWrite: typeof apiModel.cost_per_1m_in_cached === 'number' ? apiModel.cost_per_1m_in_cached : 0,
```

**Flow:** sync script fetches `/v1/provider` → transforms each entry (this remap) → regenerates models.json + README → embedded import feeds the runtime transform, which repeats the SAME remap on live fetches. Pre-`49f661b` the mapping was `cacheRead = in_cached, cacheWrite = 0` with a comment claiming "Hyper exposes discounted cached-INPUT pricing, not cache-write" — that semantic claim was WRONG and both twins were inverted together.
**Invariant:** host semantics are direction-of-the-READ: `cacheRead` prices tokens served from provider-side cache on the OUTPUT side of the turn; `cacheWrite` prices the discounted re-read of previously-cached INPUT. The trap is assuming "cached input ⇒ cacheRead" because the field NAME says read — the mapping follows HOST token-accounting semantics, not the API's field names. The two transforms (offline generator + runtime live-fetch) MUST change together or committed models.json rows contradict live-fetched ones for the same id. Zero-fallback guards (`|| 0` / `typeof === 'number'`) are per-field so one absent price never poisons siblings.
**Probe:** direct test `tests/status.smoke.ts` covers none of this plane (catalog transform) — deterministic probes instead: `bash -c 'cd $REFERENCE_ROOT/pi-hypercharm-provider && grep -c cost_per_1m_out_cached index.ts scripts/update-models.js'` → 1 file : 1 file; `grep -n "cacheWrite: 0" index.ts` → NO match (the old constant is gone); committed `models.json` rows carry non-zero cacheWrite where the API reports it (782-line golden snapshot). Coverage caveat recorded.
**Coverage caveat:** untested upstream; models.json doubles as de-facto golden fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "transformApiModel cacheRead cost_per_1m_out_cached", limit: 3 });
// → pi-hypercharm-provider.transformApiModel Function index.ts 266-300
```

## Verdict
Adopt the direction-of-the-read remap whenever your host distinguishes cacheRead/cacheWrite but your API exposes cached-input/cached-output prices — and treat offline generators + runtime transforms as ONE contract that drifts together. Omit Charm-specific field names.
