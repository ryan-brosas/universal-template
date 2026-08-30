<!-- capsule-v2 -->
# React-query data-module recipe — what is the exact shape of a `*-query.ts` data module, and how does the global retry gate consume retryAfter/requestPathname?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** How should each data module be structured so cache keys, abort signals, error conversion, and retry policy compose without per-module boilerplate drift?

## Module recipe + global QueryClient gate
**Path/Symbol:** `apps/studio/data/replication/sources-query.ts:10-48` (exemplar module); `apps/studio/data/replication/keys.ts:1-34` (keys factory); `apps/studio/data/query-client.ts:14-105` (global gate); `apps/studio/data/replication/utils.ts:18-38` (per-hook retry override).
**Signature:** `useReplicationSourcesQuery<TData>({projectRef}, {enabled, ...options}?)` returning `useQuery<ReplicationSourcesData, ResponseError, TData>`; global `getQueryClient(): QueryClient`.
**Data Shape:** keys root at `['projects', projectRef, ...]` (the exact prefix the contextual-invalidation sweep matches); errors reaching the hook are ResponseError instances carrying code/requestId/retryAfter/requestPathname from the middleware plane.

### Decisive source
```ts
// sources-query.ts — the module recipe
async function fetchReplicationSources({ projectRef }, signal?: AbortSignal) {
  if (!projectRef) throw new Error('projectRef is required')
  const { data, error } = await get('/platform/replication/{ref}/sources', {
    params: { path: { ref: projectRef } }, signal,
  })
  if (error) handleError(error)
  return data
}
export type ReplicationSourcesData = Awaited<ReturnType<typeof fetchReplicationSources>>

export const useReplicationSourcesQuery = ({ projectRef }, { enabled = true, ...options } = {}) =>
  useQuery({
    queryKey: replicationKeys.sources(projectRef),
    queryFn: ({ signal }) => fetchReplicationSources({ projectRef }, signal),
    enabled: enabled && typeof projectRef !== 'undefined',
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    retry: checkReplicationFeatureFlagRetry,
    ...options,
  })
```
```ts
// query-client.ts — the global gate that reads the enriched fields
retry(failureCount, error) {
  // Don't retry on 4xx errors
  if (error instanceof ResponseError && error.code !== undefined &&
      error.code >= 400 && error.code < 500 && error.code !== 429) return false
  // Skip retries for specific pathnames to avoid unnecessary load
  // CRITICAL: We must still retry 429 (rate limit) errors even on these pathnames.
  if (error instanceof ResponseError && error.requestPathname &&
      SKIP_RETRY_PATHNAME_MATCHERS.some((matchFn) => matchFn(error.requestPathname!)) &&
      error.code !== 429) return false
  return failureCount < MAX_RETRY_FAILURE_COUNT /* 3 */
},
retryDelay(failureCount, error) {
  if (error instanceof ResponseError && error.retryAfter) return error.retryAfter * 1000
  return Math.min(1000 * 2 ** failureCount, 30000)
},
refetchOnWindowFocus(query) {
  if (isQueryEndpointStatementTimeout(query.state.error)) return false
  return true
}
```

**Flow:** component → hook → key from factory → fetch fn throws on missing params, calls the typed client, converts `{error}` envelopes via handleError → failures bubble as classified ResponseError → global gate decides retry by code class, then pathname denylist (both with a 429 carve-out), backs off by server-sent retryAfter seconds else capped doubling, and suppresses window-focus/reconnect refetch after pg-meta statement timeouts. Per-hook overrides (e.g. stop early on 503 feature-flag or local-ETL-missing errors) replace only the retry slot; everything else inherits.
**Invariant:** every key family roots at `['projects', projectRef]` — this is load-bearing twice (invalidation prefix sweep + per-project cache isolation); `enabled` must AND caller intent with param-definedness (`typeof projectRef !== 'undefined'`) so disabled-by-default is impossible to forget; the fetch fn must thread react-query's AbortSignal into the typed call; `if (error) handleError(error)` relies on handleError's `never` return so TypeScript narrows past it.
**Probe:** direct test coverage for this recipe is structural (handleError.test.ts covers the conversion step; no upstream test pins sources-query.ts itself) — caveat recorded; probe by construction: render the hook with `projectRef: undefined` and assert zero network calls (enabled-gate), then with a ref and assert exactly one GET carrying the minted X-Request-Id.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "useQuery queryKey replicationKeys useReplicationSourcesQuery", limit: 10 });
```

## Verdict
Adopt the five-part module skeleton verbatim (private fetch fn / exported Awaited type / keys factory / hook with signal threading + enabled-gating / derived selector hooks on top) and the global-gate arithmetic including BOTH 429 carve-outs — dropping them turns rate limits into request storms (in-source CRITICAL comment). Adapt staleTime, denylist paths, and statement-timeout detection to your API surface. Omit Supabase's specific endpoint vocabulary.
