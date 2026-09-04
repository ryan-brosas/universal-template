<!-- capsule-v2 -->
# Stats dashboard client — bounded, abortable, stale-while-revalidated views

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi` (code-grounded). **Path:** `packages/stats/src/aggregator.ts`, `client/api.ts`, `client/data/useResource.ts`. **Question:** How should a dashboard client fetch typed projections without ever fabricating data or letting stale responses overwrite fresh ones?

## Provider projection: honest, range-bounded dashboard data
**Path/Symbol:** `aggregator.ts:getProviderDashboardStats` (552), `computeUsageWindowStats` (usage-windows.ts:259), `sumFleetTokens` (177); `client/api.ts:ApiError` (17), `fetchJson` (29).
**Signature:** `getProviderDashboardStats(range?): Promise<ProviderDashboardStats>`; `computeUsageWindowStats(rows, capacity): { usageSeries, windowInsights }`.
**Data Shape:** provider payload carries per-provider totals, usage series, and window insights (fraction consumed, cycles, est. tokens/window, peak, ideal accounts, exhaustion); fleet tokens come from remote installs.

### Decisive source
```ts
const res = await fetch(endpoint, options);
if (!res.ok) throw new ApiError(res.status, endpoint, `HTTP error ${res.status} on ${endpoint}`);
return res.json() as Promise<T>;
```

**Flow:** the server initializes its DB, bounds aggregation to the requested range, computes window insights from snapshot deltas, then serves typed projections; the client URL-encodes its range, forwards an `AbortSignal`, and surfaces non-ok HTTP as `ApiError` rather than a hollow payload.

**Invariant:** fleet-token results are null/empty — not faked zero — when no report exists; per-install windows must not be misread as fleet totals. The client never fabricates data a closed dashboard endpoint withheld.

**Probe:** `test/provider-stats.test.ts` covers server projection deltas, resets, per-provider totals, and fleet token inference; the dashboard consumes these typed routes.

## Client data hook: instant cache, cancellable revalidation
**Path/Symbol:** `client/data/useResource.ts:useResource` (24), `RESOURCE_CACHE_LIMIT = 64` (22); types `ResourceResult`, `ResourceOptions`.
**Signature:** `useResource<T>(key: readonly unknown[], fetcher, options?): ResourceResult<T>`.
**Data Shape:** `ResourceResult { data, error, loading, refreshing, refetch, updatedAt }`; `ResourceOptions { pollMs?, enabled? }`; an in-memory stale-while-revalidate cache (keyed by serialized key, capped at 64) scoped to the session.

### Decisive source
```ts
const controller = new AbortController();
controllerRef.current = controller;
if (cached) { setData(cached.data as T); executeRefetch(true); }
```

**Flow:** first load shows a skeleton; revisiting a key renders cached data THEN revalidates in the background; toggling the key aborts the prior request and re-tunes without unmounting; optional polling when `pollMs` is set.

**Invariant:** an aborted or out-of-order response must never overwrite more recent data; the cache is session-local, ephemeral, disposable — never a durable ledger.

**Probe:** `test/client-view-models.test.ts` and the provider-stats test cover the provider projection and its consumption. Coverage caveat: tests excluded from graph index by design.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(getProviderDashboardStats|computeUsageWindowStats|sumFleetTokens|useResource|fetchJson)$", limit: 6, fields: ["signature"] });
```

## Verdict
Adopt typed projections with ApiError surfacing, null-not-zero fleet semantics, capped SWR caches with abort-on-key-change, and snapshot-delta window insights; adapt route shapes and cache limits to host frameworks; omit the broker/fleet plumbing unless multi-account reporting is needed.
