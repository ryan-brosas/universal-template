<!-- capsule-v2 -->
# Stale-while-revalidate model sync — how do you serve a provider catalog with zero startup latency yet keep it fresh?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How does an extension ship a model list that renders instantly from embedded data, self-heals against a live API, and survives cold caches — without ever blocking registration?

## Serve-stale → revalidate → hot-swap ladder
**Path/Symbol:** `index.ts:234-239` (`PROVIDER_ID`/`BASE_URL`/`MODELS_URL`/`CACHE_PATH`), `LIVE_FETCH_TIMEOUT_MS = 8_000` :239; `loadCachedModels` `index.ts:318-326`, `cacheModels` `index.ts:327-335`, `loadStaleModels` `index.ts:395-407`, `revalidateModels` `index.ts:409-416`; wired at default-export entry `index.ts:1013-1025` + hot-swap in session_start `index.ts:1057-1062`.
**Signature:** `loadStaleModels(embedded: JsonModel[]): JsonModel[]`; `revalidateModels(apiKey?: string, embedded: JsonModel[], signal?): Promise<JsonModel[] | null>`.
**Data Shape:** three independent sources ranked by freshness — disk cache `<agentDir>/cache/hypercharm-models.json`, embedded `models.json` import, live `/v1/provider`. All degrade to `null`/fallback silently (try/catch returns null; non-ok response returns null; empty array returns null).

### Decisive source
```ts
function loadStaleModels(embeddedModels: JsonModel[]): JsonModel[] {
	const cached = loadCachedModels();
	if (!cached || cached.length === 0) return embeddedModels;
	// Merge embedded models that are missing from cache (newly added models)
	const cachedMap = new Map(cached.map(m => [m.id, m]));
	for (const em of embeddedModels) {
		if (!cachedMap.has(em.id)) cached.push(em);
	}
	return cached;
}

async function revalidateModels(apiKey, embeddedModels, signal) {
	if (!apiKey) return null;
	const liveModels = await fetchLiveModels(apiKey, signal);
	if (!liveModels || liveModels.length === 0) return null;
	const merged = mergeWithEmbedded(liveModels, embeddedModels);
	cacheModels(merged);
	return merged;
}
```
(`fetchLiveModels`, `index.ts:302-317`, hard-caps the call with `AbortSignal.any([AbortSignal.timeout(8000), signal])` and accepts `data | data.models | data.data` array shapes.)

**Flow:** default-export entry builds stale list synchronously (`buildModels(loadStaleModels(embedded), custom, patch)`) and calls `pi.registerProvider` BEFORE any async work → `session_start` aborts the previous revalidation controller (`revalidateAbort?.abort()`, `:1033-1035`) → resolves key (epoch-vetoed, see stale-ctx-epoch-guard.md) → fires `revalidateModels` in the background → on success AND still-current epoch AND still-not-aborted it rebuilds `currentModels` and re-registers the provider, hot-swapping the catalog mid-session.
**Invariant:** registration NEVER awaits the network. A failed/timed-out/keyless revalidation leaves the stale list serving — every failure path returns `null` and the caller ignores it. Cache reads are defensively merged with embedded so a stale cache missing a newly shipped model cannot hide it. Re-registration after swap goes through the same `makeProviderConfig()` factory (`index.ts:1000-1011`) so the streaming handler and the model list can never desync (its custom `api: "hypercharm"` name also guarantees the extension's own `streamSimple` registers as a distinct handler and never shadows pi's built-in openai-completions pipeline). The swap is additionally gated on the session epoch — a catalog landing after a fast /new must not mutate the new session's registration from the old session's chain.
**Probe:** no upstream test runner covers the runtime path — deterministic check instead: `node --check index.ts` plus the fact that `pi.registerProvider(...)` at `:1022` runs before the first `await` in `export default function (pi)` (`:1013`; source-read `:1013-1065`). Record as coverage caveat.
**Coverage caveat:** cited paths verified `no_recorded_issue` via check_index_coverage; runtime event path untested upstream.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "revalidateModels", limit: 5 });
// → pi-hypercharm-provider.revalidateModels Function index.ts 409-416
```

## Verdict
Adopt the whole ladder (serve stale synchronously, revalidate in background, hot-swap via one config factory, abort-on-new-session). Adapt cache location and timeout budget to your host. Omit Charm-specific `/v1/provider` shapes and the hypercredit unit comments.
