<!-- capsule-v2 -->
# Offset vs cursor pagination envelopes — how does v2 page math coexist with v3 HATEOAS links, and when does pageInfo drop `page`?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Why can PagedResponseImpl DELETE pageInfo.page, and what must the v3 link builder preserve?

## Fractional-page fallback + query-preserving links
**Path/Symbol:** `packages/nocodb/src/helpers/PagedResponse.ts:PagedResponseImpl` (:48–96), `PagedResponseV3Impl` (:98–184).
**Signature:** `new PagedResponseImpl(list, {limit?, offset?, count?, l?, o?, limitOverride?, page?}, additionalProps?)`; `new PagedResponseV3Impl(pagedResponse, {context, baseUrl?, tableId, nestedNextPageAvail?, nestedPrevPageAvail?, queryParams?})`.
**Data Shape:** v2 pageInfo = {totalRows, page?, pageSize, isFirstPage, isLastPage, offset?}; v3 pageInfo = {prev?, next?, nestedNext?, nestedPrev?} absolute URLs; commonQueryParams allowlist = sort, where, viewId, pageSize, fieldIdOnResult, fields, nestedPage, linksAsLtar.

### Decisive source
```ts
if (this.pageInfo.page % 1 !== 0) {
  this.pageInfo.offset = offset;
  delete this.pageInfo.page;
}

if (offset && offset >= +count) {
  NcError.invalidOffsetValue(offset);
}
...
if (!pagedResponse.pageInfo.isFirstPage && pagedResponse.pageInfo.page) {
  pageInfo.prev = constructUrl({
    ...commonProps,
    query: { ...commonQueryParams, page: pagedResponse.pageInfo.page - 1 },
  });
}
```
(:80–:87, :141–:145)

**Flow:** v2 — with a count, derive page from offset/limit+1, compute isLastPage via ceil(totalRows/pageSize) (||1 guards zero rows); if offset/limit yields a FRACTIONAL page the envelope degrades to explicit offset and deletes page rather than lie → offset beyond totalRows throws invalidOffsetValue → additionalProps merged last so callers attach errors[] etc. v3 — build prev/next ONLY when the flags say a neighbor exists, carrying the allowlisted query params forward; nested prev/next paginate the CHILD list inside the same parent page (nestedPage ±1 clamped ≥1 at read).
**Invariant:** the v3 link builder must round-trip EXACTLY the params it received minus pagination keys it rewrites — dropping sort/where/viewId would silently change the next page's content; that's why extractProps allowlists them explicitly. linksAsLtar rides the common set because nested-row shape changes downstream parsing. v2's delete-page-on-fractional-offset keeps clients from computing wrong next pages.
**Probe:** `cd packages/nocodb && grep -c "isLastPage\|isFirstPage" src/helpers/PagedResponse.ts` (=5) and `grep -c "invalidOffsetValue" src/helpers/PagedResponse.ts` (=1) and `grep -c "nestedPage" src/helpers/PagedResponse.ts` (=4) and `grep -c "linksAsLtar" src/helpers/PagedResponse.ts` (=1).
**Direct test:** none upstream for helpers/PagedResponse.ts — grep probes pin shape.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "PagedResponseV3Impl PagedResponseImpl pageInfo nestedNext", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flag-gated link construction + param allowlist round-trip + fractional-page degradation; adapt path/query shapes to your API versioning; omit v2 math if you are cursor-only. Coverage caveat: grep-pinned only.
