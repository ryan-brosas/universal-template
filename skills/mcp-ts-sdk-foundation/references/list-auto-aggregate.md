<!-- capsule-v2 -->
# Paginated list auto-aggregate — how do you walk every page of a server-driven cursor list and cache ONE aggregate without caching a lie?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What guards does an auto-draining `listTools()` need against non-converging pagination, mid-walk invalidations, and cache-poisoning by partial results?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/client.ts`: `_listAllPages` (:1714-1768), `_freshness` (:1782-1795); cap constant `DEFAULT_LIST_MAX_PAGES` (64) wired at :655; typed error `SdkErrorCode.ListPaginationExceeded`.
**Signature:** `_listAllPages<R extends {nextCursor?:string}>(method, baseParams, options, append: (acc,page)=>void, finalize?: (acc)=>void): Promise<R>` — no-`cursor` calls auto-aggregate; explicit `{cursor}` callers get the per-page path unchanged.
**Data Shape:** Page 1's result object is mutated in place (items array extended, `nextCursor` DELETED — not `= undefined`, because the JSON codec drops explicit-undefined keys and `'nextCursor' in result` must stay identical between wire and cache hit). baseParams thread into EVERY page request so documented `_meta` (e.g. W3C trace context) reaches each wire call.

### Decisive source
```ts
while (cursor !== undefined && !seen.has(cursor)) {
    if (this._listMaxPages !== 0 && pages >= this._listMaxPages)
        throw new SdkError(SdkErrorCode.ListPaginationExceeded,
            `${method}: exceeded listMaxPages (${this._listMaxPages}); server pagination did not terminate`, …);
    seen.add(cursor);
    const page = await this.request({ method, params: { ...baseParams, cursor } }, options);
    append(acc, page); cursor = page.nextCursor; pages++;
}
delete acc.nextCursor;
// The aggregate is ALWAYS written: even TTL ≤0 stores it already-stale
// (retain-for-schema posture) while the freshness gate never serves it.
await this._cache.write(method, acc, generation, this._freshness(acc));
```

**Flow:** captureGeneration BEFORE page 1 (mid-walk `list_changed` bumps ⇒ terminal write skips) → request page 1 → walk with repeated-cursor detection (`seen` set — defence against non-converging servers) under the hard cap → finalize hook runs on the COMPLETE aggregate (SEP-2243 invalid-header exclusion filters here so the cached entry is pre-filtered) → single cache write carrying page-1's ttl/cacheScope.

**Invariant:** Hitting the cap THROWS — a partial aggregate is never cached and never returned. A repeated nextCursor stops the walk. Serialization doubles as mutation barrier: the caller mutating the returned aggregate cannot reach the store or derived indices. Always-write-even-stale keeps the tools/list-derived name index working while freshness gating prevents stale serving.

**Probe:** `packages/client/test/client/responseCache.test.ts` :475 ("the auto-aggregate path throws SdkError(ListPaginationExceeded) when listMaxPages is hit and does not write a partial entry").

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "_listAllPages ListPaginationExceeded _freshness", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt fail-loud capping + seen-set loop guard + capture-before-walk write suppression for any aggregate-over-cursor API; adapt cap default and finalize hooks; omit the retain-stale-for-schema trick if you have no derived index.
