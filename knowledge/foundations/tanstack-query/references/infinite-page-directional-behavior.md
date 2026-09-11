<!-- capsule-v2 -->
# infiniteQueryBehavior directional page walker — how does one behavior hook produce forward/backward/refetch page walks?

**Source:** TanStack Query MIT `main@bc423b37ef7fa2a34cfc7286945fd640d74b4071`; Codebase Memory `ext-ui-tanstack-query`. **Question:** How can a behavior plugin rewrite a query's fetchFn to accumulate pages, honor fetchNextPage/fetchPreviousPage, and respect maxPages — while the retryer stays unchanged?

## onFetch fetchFn replacement
**Path/Symbol:** `packages/query-core/src/infiniteQueryBehavior.ts:infiniteQueryBehavior` (:16–130); selected by `Query.fetch` (:517–523) when `_type === 'infinite'`.
**Signature:** `infiniteQueryBehavior(pages?: number): QueryBehavior` — `{ onFetch(context, query) }` mutates `context.fetchFn`.
**Data Shape:** result `{ pages: unknown[], pageParams: unknown[] }`; direction from `context.fetchOptions.meta.fetchMore.direction`.

### Decisive source
```ts
// fetch next / previous page?
if (direction && oldPages.length) {
  const previous = direction === 'backward'
  const pageParamFn = previous ? getPreviousPageParam : getNextPageParam
  const oldData = { pages: oldPages, pageParams: oldPageParams }
  const param = pageParamFn(options, oldData)
  result = await fetchPage(oldData, param, previous)     // ONE page appended/prepended
} else {
  const remainingPages = pages ?? oldPages.length
  do {
    const param = currentPage === 0
      ? (oldPageParams[0] ?? options.initialPageParam)
      : getNextPageParam(options, result)
    if (currentPage > 0 && param == null) break          // hasNextPage == false stops the walk
    result = await fetchPage(result, param)
    currentPage++
  } while (currentPage < remainingPages)
}
```
with cancellation inside fetchPage:
```ts
if (cancelled) return Promise.reject(context.signal.reason)
if (param == null && data.pages.length) return Promise.resolve(data)
```
and trimming:
```ts
const addTo = previous ? addToStart : addToEnd
return { pages: addTo(data.pages, page, maxPages), pageParams: addTo(data.pageParams, param, maxPages) }
```

**Flow:** initial/refetch walk loops from pageParams[0]/initialPageParam until getNextPageParam returns null or remainingPages exhausted; fetchNextPage/meta.direction=forward appends exactly ONE page derived from the LAST page's param; backward prepends via getPreviousPageParam. The consume-aware signal (`addConsumeAwareSignal`) marks `cancelled` only if the queryFn actually READ context.signal — unread signals never abort mid-walk.
**Invariant:** (1) pages and pageParams are trimmed TOGETHER by maxPages (addToEnd/addToStart share one cap arg) — desyncing them breaks param↔page correspondence forever; (2) refetch re-walks ALL pages from stored pageParams (pageParams ARE the resume cursor), not from scratch; (3) null/undefined param is the universal stop sentinel (`== null`, catching both); (4) the retryer wraps the WHOLE walker — a failure on page N of M retries the entire fetchFn, and oldPages restore happens inside via closure over state.
**Probe:** `grep -n "direction === 'backward'" packages/query-core/src/infiniteQueryBehavior.ts` (:84 once) and `grep -n "remainingPages" packages/query-core/src/infiniteQueryBehavior.ts` (:94/:107); direct tests `__tests__/infiniteQueryBehavior.test.tsx` + `__tests__/query.test.tsx` maxPages matrix.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-tanstack-query", name_pattern: "^getNextPageParam$|^hasNextPage$", limit: 5 });
```

## Verdict
Adopt behavior-as-fetchFn-rewriter for composable fetch shapes (streams, pagination, SSR). Adapt param derivation to your API cursors; keep the dual-plane trim rule. Omit getPreviousPageParam optional support if forward-only. Direct tests: infiniteQueryBehavior.test.tsx.
