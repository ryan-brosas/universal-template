<!-- capsule-v2 -->
# Tiered memory index — how do you index 1,000+ sessions under hard byte budgets while keeping search coverage honest?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the hot/cold tier contract, and what makes a cache entry trustworthy?

## Hot shards / cold digests + self-referential cache metrics
**Path/Symbol:** `src/memory/index.ts:loadTieredIndex` (:660-763), `loadShard` (:307-361), `hydrateShard` (:363-413), `loadDigest` (:484-545), `fitDigestCache` (:458-482), `classifySessionTiers` (:552-559), `cleanupCacheDirectory` (:578-649), `applyCacheMetrics` (:215-229).
**Signature:** `loadTieredIndex(refs, allRefs, options, hydrate=false, entryRange?): {shards, digests, refs, tiers, coverage}`; `MEMORY_CACHE_VERSION = 6`; defaults hot=50, maxSyncSessions=10_000, maxSyncSourceBytes=512 MiB, cold cache ≤1 MiB, vocabulary ≤512 KiB.
**Data Shape:** Shard = full normalized entries + `{cacheVersion, kind:"shard", mtime,size,sourceHash(64-hex),branches,lineageFingerprint,policy,cacheBytes,cacheSourceRatio,indexCoverage{complete,reasons[]}}`; DigestShard = same header over `{vocabulary (sorted), addresses (10-tuples)}` with NO entries. Cache filenames embed a sha1-of-path prefix + sanitized basename + `.all` suffix for branches:"all".

### Decisive source
```ts
// cacheBytes records the size of the record CONTAINING cacheBytes — fixed point
const applyCacheMetrics = <T extends CacheRecord>(value: T): T => {
  let previous = -1;
  for (let iteration = 0; iteration < 5; iteration += 1) {
    const bytes = serializedBytes(value);
    value.cacheBytes = bytes;
    value.cacheSourceRatio = value.size === 0 ? 0 : Number((bytes / value.size).toFixed(6));
    if (bytes === previous) break;
    previous = bytes;
  }
  ...
};
```
```ts
// TOCTOU guard: fingerprint BEFORE and AFTER the expensive normalization;
// a source or lineage change mid-index discards the work under a NAMED reason
const finalState = fingerprintSource(ref.file);
const finalLineage = resolveLineage(ref.file, options);
if (!finalState || finalState.sourceHash !== state.sourceHash ||
    finalLineage.fingerprint !== lineage.fingerprint) {
  removeCacheFile(filePath);
    return missingShard(
      ref,
      finalLineage,
      finalState?.sourceHash === state.sourceHash
        ? "lineage_changed_during_index"
        : "source_changed_during_index",
    );
```

**Flow:** cleanup pass first (budget-capped: stops at maxFiles/maxBytes with reason `cache_cleanup_budget`; deletes files whose recomputed canonical path ≠ their name, whose source vanished, or that fail structural revalidation — non-JSON and unreadable entries are removed unconditionally) → tiers assigned by mtime recency (ties broken lexically) → hot tier loads FULL shards and DELETES the sibling digest file; cold tier loads digests and deletes sibling shard files (tiers never both persist) → per-session admission: skip missing sources (`source_unavailable`), stop admitting past `max_sync_sessions`, estimate work as `size × (hydrate&&cold ? 6 : 3)` against `max_sync_source_bytes` → every skip/failure accumulates into `coverage.reasons`; coverage.complete is false unless cleanup completed AND zero sessions stale AND zero incomplete. `fitDigestCache` shrinks an over-budget digest by binary-searching the longest fitting PREFIX of addresses, then of vocabulary, flipping `indexCoverage.complete=false` with reason `max_cold_cache_bytes` — completeness is sacrificed loudly, addresses before vocabulary.
**Invariant:** a cache file is trusted only when version, kind, exact path identity, 64-char source hash, lineage fingerprint, policy string, AND `parsed.cacheBytes === stat.size` all match — self-describing size makes truncation/corruption detectable without parsing heuristics; privacy policy (`thinking:…;tool-output:…`) is part of `policy`, so flipping an indexing-privacy flag invalidates caches BY CONSTRUCTION.
**Probe:** `tests/memory-cache-v6.test.ts:87` ("searches every eligible session despite maxSessions … ranks the oldest rare fact first" — coverage complete at indexedSessions=1001, oldest-rare ranks #1 in hot AND regex AND unicode arms; also pins dir mode 0700/file 0600), `:182` ("rebuilds rewritten and V5 caches and removes caches for deleted sources"), `tests/memory.test.ts:292-330` (shard freshness + bm25 ranking).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "loadTieredIndex loadShard loadDigest fitDigestCache applyCacheMetrics classifySessionTiers cleanupCacheDirectory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier split, self-referential metrics validation, double-fingerprint TOCTOU guard, and prefix-fit loud-degradation shrink; adapt budgets and the work-estimate multiplier to your host; omit the pi session-normalization specifics feeding it. Direct tests cited (1,001-session integration); graph coverage clean.
