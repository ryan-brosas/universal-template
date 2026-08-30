<!-- capsule-v2 -->
# Voyager filter grammar serializer — `List(key|value)` query encoding for private-API search (how do I encode structured filters into a restli query string)?

**Source:** linkedin-private-api MIT `master@e083f37`; Codebase Memory `linkedin-private-api`. **Question:** LinkedIn's voyager endpoints take filters as pseudo-typed query params (`filters=List(currentCompany->X,network->F)`) — what exact grammar and serialization order produces valid URLs?

## The serializer
**Path/Symbol:** `src/utils/paramsSerializer.ts:paramsSerializer/encodeFilter` (:4–28); consumers `src/requests/search.request.ts:searchBlended/searchJobs` (:14–71).
**Signature:** `paramsSerializer(params: Record<string, string | Record<string, string>>): string`; `encodeFilter = (value: string | string[], key: string) => encodeURIComponent(`${key}->${castArray(value).join('|')}`)`.
**Data Shape:** scalars pass through `.toString()`; arrays become `List(a,b,c)`; objects (filter dicts) become `List(k1->v1,k2->v2a|v2b)` — multi-value filters join with `|` INSIDE one `key->` clause; final assembly via `stringify(encodedParams, undefined, undefined, { encodeURIComponent: uri => uri })` so pre-encoded values are NOT double-escaped.

### Decisive source
```ts
const encodedParams = mapValues(params, value => {
  if (!isArray(value) && !isPlainObject(value)) { return value.toString(); }
  if (isArray(value)) { return `List(${value.join(',')})`; }
  const encodedList = reduce(value as Record<string, string>,
    (res, filterVal, filterKey) => `${res}${res ? ',' : ''}${encodeFilter(filterVal, filterKey)}`, '');
  return `List(${encodedList})`;
});
return stringify(encodedParams, undefined, undefined, { encodeURIComponent: uri => uri });
```

**Flow:** request builds a plain dict (`{ filters: { resultType: 'PEOPLE', network: 'F' }, count, start, keywords?, origin: 'TYPEAHEAD_ESCAPE_HATCH', q: 'all', queryContext }`) → serializer turns ONLY the nested dict into the List() grammar → axios custom paramsSerializer emits the final query string. Job-search twin swaps endpoint semantics in the SAME param dict shape: `q: 'jserpFilters'`, `origin: 'JOB_SEARCH_RESULTS_PAGE'`, plus a versioned `decorationId: 'com.linkedin.voyager.deco.jserp.WebJobSearchHitLite-14'` that selects the response decoration.
**Invariant:** keywords are `encodeURIComponent`-ed BY THE CALLER before reaching the serializer (:28–29/:57), then protected from re-encoding by the identity `encodeURIComponent` option — double-encoding is the classic wrong port. Filter keys use ASCII `->`, multi-values use `|`, list elements use `,`; all three are reserved by this grammar and must not appear raw in values. The `count`/`start` names (NOT limit/skip) are what hits the wire.
**Probe:** `test/search/search-repository.spec.ts:26–78` stubs match `matchers.contains({ start: 0, count: 10, filters: { resultType: 'PEOPLE' } })` and keywords pre-encoded via `encodeURIComponent(keywords)` — pinning both the param names and the caller-side keyword escaping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-private-api", query: "paramsSerializer encodeFilter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-separator grammar (`->`, `|`, `,` inside `List(...)`) + identity-final-encode + caller-side keyword escaping for any List()-typed API surface. Adapt origin/q/decorationId constants per endpoint generation. Contrast in-suite: joeyism/open-linkedin-api build these strings by hand (voyager-search-facet-encoding) — this repo's serializer is the reusable kernel behind that ad-hoc code. Direct tests pin the wire format at param-dict level.
