<!-- capsule-v2 -->
# Project allow-list policy — how does per-project policy constrain subs, pools, and chains without mutating global config?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** How do you scope routing to an exact set of accounts for one project while keeping the global config untouched and chains coherent?

## EffectiveConfig folds global + project into a filtered view
**Path/Symbol:** `extensions/multi-sub.ts`: `normalizeAllowedProviderNames` (1625-1629), `filterPoolsByAllowedProviders` (1631-1645), `filterChainsByAvailablePools` (1647-1655), `loadEffectiveConfig` (1657-1694); runtime enforcement `enforceProjectRestriction` (multiSub, 5400-5439).
**Signature:** `function loadEffectiveConfig(cwd: string): EffectiveConfig`; `function filterPoolsByAllowedProviders(pools: PoolConfig[], allowedProviderNames: string[] | undefined): PoolConfig[]`; `function filterChainsByAvailablePools(chains: ChainConfig[], pools: PoolConfig[]): ChainConfig[]`.
**Data Shape:** ProjectConfig (.pi/multi-pass.json) = {pools?, chains?, allowedSubs?}; project.pools/chains REPLACE global wholesale when present. EffectiveConfig adds `allowedProviderNames?: string[]` (deduped, trimmed) and `projectConfigPath?`.

### Decisive source
```ts
const allowedProviderNames = normalizeAllowedProviderNames(project.allowedSubs);
let subs = mergedSubscriptions;
if (allowedProviderNames) {
	const allowed = new Set(allowedProviderNames);
	subs = mergedSubscriptions.filter((s) => allowed.has(subProviderName(s)));
}

let pools = project.pools !== undefined ? project.pools : global.pools;
let chains = project.chains !== undefined ? project.chains : global.chains;
if (allowedProviderNames) {
	pools = filterPoolsByAllowedProviders(pools, allowedProviderNames);
	chains = filterChainsByAvailablePools(chains, pools);
}
```

**Flow:** load global -> merge env subscriptions -> load .pi/multi-pass.json if present -> no project file means pure global view -> otherwise: exact allow-list filters subscriptions by full provider NAME (not base type), pool members are filtered per pool, pools emptied by filtering are DROPPED entirely, then chain entries whose target pool no longer exists are removed and chains left with zero entries are dropped.
**Invariant:** the allow-list is EXACT-match on derived account names ("openai-codex-2"), never prefix/base-provider matching; filtering is order-dependent — subs, then pools, then chains against the SURVIVING pool names — so no chain can reference a pool that was pruned; the global file is never mutated (the fold produces a fresh view each call).
**Probe:** `node tests/project-restriction-check.mjs` (runExactProviderRestrictionCheck pins exact-name restriction incl. filterPools/filterChains helpers; green at b9d9d1d7a092).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "loadEffectiveConfig filterPoolsByAllowedProviders filterChainsByAvailablePools", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt the three-stage exact allow-list fold (subs -> pool members -> chain coherence) as a pure function producing a per-scope view. Adapt where the project policy lives and how restriction is enforced at switch time (enforceProjectRestriction's in-flight guard prevents recursive model switches). Omit the pi session_start/model_select/input event wiring.
