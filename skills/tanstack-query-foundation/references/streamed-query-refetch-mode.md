<!-- capsule-v2 -->
# streamedQuery refetch modes — how does an AsyncIterable stream land in the cache chunk-by-chunk?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How can a queryFn emit progressive updates (pending → success on first chunk, fetching until stream end) with three distinct refetch behaviors?

## streamedQuery factory
**Path/Symbol:** `packages/query-core/src/streamedQuery.ts:streamedQuery` (:51–120).
**Signature:** `streamedQuery<TQueryFnData, TData, TQueryKey>({streamFn, refetchMode = 'reset', reducer = addToEnd, initialValue = []}): QueryFunction<TData>`; reducible overload takes custom reducer+initialValue.
**Data Shape:** cache data accumulates through setQueryData per chunk (reset/append) or one final write (replace).

### Decisive source
```ts
const isRefetch = !!query && query.isFetched()
if (isRefetch && refetchMode === 'reset') {
  query.setState({ ...query.resetState, fetchStatus: 'fetching' })   // back to pending NOW
}
...
let cancelled: boolean = false
const streamFnContext = addConsumeAwareSignal({client, meta, queryKey, pageParam, direction},
  () => context.signal,
  () => (cancelled = true))
const stream = await streamFn(streamFnContext)
const isReplaceRefetch = isRefetch && refetchMode === 'replace'
for await (const chunk of stream) {
  if (cancelled) break
  if (isReplaceRefetch) {
    result = reducer(result, chunk)                    // buffer locally
  } else {
    context.client.setQueryData(context.queryKey, (prev) => reducer(prev === undefined ? initialValue : prev, chunk))
  }
}
// finalize result: replace-refetching needs to write to the cache
if (isReplaceRefetch && !cancelled) {
  context.client.setQueryData(context.queryKey, result)
}
return context.client.getQueryData(context.queryKey) ?? initialValue
```

**Flow:** reset mode wipes to resetState BEFORE streaming (UI returns to pending skeletons); append mode folds each chunk straight into the cache via functional setQueryData; replace mode buffers and writes once after a CLEAN stream end (`!cancelled`). The signal is consume-aware: only queryFns that read context.signal get abort propagation, which flips `cancelled` and breaks the loop at the next chunk boundary.
**Invariant:** (1) 'pending until first chunk, success after, fetchStatus fetching until end' falls out of real dispatches — each setQueryData is a manual success that does NOT idle fetchStatus (the dispatch-reducer manual rule), so progress renders live; (2) replace-refetch discards partial work on cancellation by never writing; append/reset keep what arrived before the break; (3) the return value re-reads from cache — the single source of truth even for replace.
**Probe:** `grep -n "refetchMode === 'reset'" packages/query-core/src/streamedQuery.ts` (:70 once) and `grep -n "isReplaceRefetch" packages/query-core/src/streamedQuery.ts` (:96/:103/:114); direct tests `__tests__/streamedQuery.test.tsx`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^streamedQuery$|^addConsumeAwareSignal$", limit: 5 });
```

## Verdict
Adopt chunked-cache-writing for LLM/SSP streams over any store exposing functional setData. Adapt reducer defaults. Omit reducible overload unless non-array accumulators are needed. Direct tests: streamedQuery.test.tsx covers all three modes + abort.
