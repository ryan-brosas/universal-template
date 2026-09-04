<!-- capsule-v2 -->
# Hydration newer-wins merge + pending-promise transfer — how does server state merge without clobbering fresher client data or in-flight promises?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** What are the exact guards that decide hydrate-vs-skip for existing queries, and how do dehydrated PENDING queries (streaming SSR) resolve on the client?

## hydrate per-query ladder
**Path/Symbol:** `packages/query-core/src/hydration.ts:hydrate` (:194–328) with `dehydrateQuery` (:121–144), `dehydratePromise` (:89–115), `tryResolveSync` (:19–36).
**Signature:** `hydrate(client, dehydratedState, options?)`; DehydratedQuery = `{queryHash, queryKey, state, promise?, meta?, queryType?, dehydratedAt?}`.
**Data Shape:** syncData = tryResolveSync(promise) — a thenable tapped SYNCHRONOUSLY via `.then` capture.

### Decisive source
```ts
const syncData = promise ? tryResolveSync(promise) : undefined
const rawData = state.data === undefined ? syncData?.data : state.data
...
if (query) {
  const hasNewerSyncData =
    syncData && dehydratedAt !== undefined && dehydratedAt > query.state.dataUpdatedAt
  if (state.dataUpdatedAt > query.state.dataUpdatedAt || hasNewerSyncData) {
    // Omit fetchStatus from dehydrated state so that query stays in its current fetchStatus
    const { fetchStatus: _ignored, ...serializedState } = state
    query.setState({
      ...serializedState,
      data,
      ...(state.status === 'pending' && data !== undefined && {
        status: 'success', dataUpdatedAt: dehydratedAt ?? Date.now(),
        ...(!existingQueryIsFetching && { fetchStatus: 'idle' }),
      }),
    })
  }
} else { /* build with fetchStatus forced 'idle' and pending+data → success promotion */ }

if (promise && !syncData && !existingQueryIsPending && !existingQueryIsFetching &&
    (dehydratedAt === undefined || dehydratedAt > query.state.dataUpdatedAt)) {
  // This doesn't actually fetch - it just creates a retryer which will re-use the passed initialPromise
  query.fetch(undefined, { initialPromise: Promise.resolve(promise).then(deserializeData) }).catch(noop)
}
```

**Flow:** dehydrate: success-status queries by default (`defaultShouldDehydrateQuery`), pending ones additionally carry `promise = query.promise.then(serialize).catch(redact)` where redaction replaces errors with a bare Error('redacted') in production and the dehydrated copy ALSO `.catch(noop)`s to avoid unhandled rejections. hydrate: try synchronously resolving the transferred promise first (fast path when the stream already flushed); newer-wins comparison uses BOTH state.dataUpdatedAt and dehydratedAt-vs-local-dataUpdatedAt for sync-resolved promises; existing fetchStatus is never overwritten; pending+data payloads get promoted to success with dehydratedAt timestamp.
**Invariant:** (1) `fetchStatus` is STRIPPED on merge — hydration can never flip a locally-fetching query to idle or vice versa; new queries force idle to avoid stuck-fetching ghosts; (2) the promise is injected as `initialPromise`, consumed by the retryer's first run() (`failureCount === 0` gate) — no network call happens; ensureQueryFn even returns a closure re-rejecting that same promise if a retry is attempted without a queryFn (:467 utils); (3) RSC-transformed promises may not be thenable — hence `Promise.resolve(promise)` re-wrap before .then; (4) tryResolveSync tolerates thenables lacking `.catch`.
**Probe:** `grep -n "hasNewerSyncData" packages/query-core/src/hydration.ts` (:242/:250 exactly 2) and `grep -n "redacted" packages/query-core/src/hydration.ts | head -3`; direct tests `__tests__/hydration.test.tsx` (46 its).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^tryResolveSync$|^dehydratePromise$", limit: 5 });
```

## Verdict
Adopt newer-wins + fetchStatus-stripping + promise-transfer verbatim for any SSR/resume boundary. Adapt serialization hooks (serializeData/deserializeData transformers) and error redaction policy. Omit mutation dehydration unless porting offline queues. Direct tests: hydration.test.tsx incl. streaming-pending suites.
