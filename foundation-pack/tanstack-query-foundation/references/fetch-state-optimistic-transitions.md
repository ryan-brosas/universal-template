<!-- capsule-v2 -->
# fetchState shared by real transitions AND render-time optimism — how does the same helper drive both?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How does the UI show `fetchStatus: 'fetching'` on the very first render — before any dispatch — without lying to observers that subscribe later?

## fetchState export
**Path/Symbol:** `packages/query-core/src/query.ts:fetchState` (lines 718–737), consumed by `queryObserver.createResult` (line 490).
**Signature:** `fetchState<TQueryFnData, TError, TData, TQueryKey>(data, options): { fetchFailureCount: 0, fetchFailureReason: null, fetchStatus: 'fetching'|'paused', error?: null, status?: 'pending' }`.
**Data Shape:** pure function of current cached data presence + networkMode.

### Decisive source
```ts
export function fetchState(data, options) {
  return {
    fetchFailureCount: 0,
    fetchFailureReason: null,
    fetchStatus: canFetch(options.networkMode) ? 'fetching' : 'paused',
    ...(data === undefined &&
      ({
        error: null,
        status: 'pending',
      } as const)),
  } as const
}
```
and its optimistic consumer:
```ts
if (options._optimisticResults) {
  const mounted = this.hasListeners()
  const fetchOnMount = !mounted && shouldFetchOnMount(query, options)
  const fetchOptionally =
    mounted && shouldFetchOptionally(query, prevQuery, options, prevOptions)
  if (fetchOnMount || fetchOptionally) {
    newState = { ...newState, ...fetchState(state.data, query.options) }
  }
  if (options._optimisticResults === 'isRestoring') {
    newState.fetchStatus = 'idle'
  }
}
```

**Flow:** real path — dispatch('fetch') spreads fetchState into the new state. Optimistic path — createResult computes whether a fetch WOULD start on mount/option-change (shouldFetchOnMount / shouldFetchOptionally ladders: enabled≠false, no-data-or-stale-by-time, retryOnMount gate for prior errors, staleTime ≠ 'static') and overlays the SAME fetchState so the first rendered result already shows fetching/paused. The `isRestoring` variant forces idle so persistence-restoration phases don't flash spinners.
**Invariant:** (1) `error: null, status: 'pending'` are added ONLY when data === undefined — a background refetch never flips status back to pending; (2) paused-vs-fetching is decided by canFetch(networkMode), i.e., offline hosts get 'paused' optimistically too; (3) the overlay happens in result-space only — query.state is untouched.
**Probe:** `grep -n "_optimisticResults" packages/query-core/src/queryObserver.ts` (:479/:493 exactly 2) and `grep -c "import { fetchState }" packages/query-core/src/queryObserver.ts` (=1).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^canFetch$", limit: 3 });
```

## Verdict
Adopt the shared-helper pattern: one function defines "what a starting fetch looks like" for both machine transitions and pre-subscription render optimism. Adapt should* ladders to your mount/refetch policy but preserve the data-undefined conditional spread. Omit isRestoring unless you have a persister restore phase.
