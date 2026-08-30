<!-- capsule-v2 -->
# Page cache admission — how can a "full" cache stay safe, and what stops soft limits from becoming duplicate or torn reads?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** When nothing can be evicted, do I fail the read — and if not, what bookkeeping keeps degradation honest?

## Soft capacity + single-flight pending reads
**Path/Symbol:** `core/storage/pager.rs` soft-limit rationale (:3405-3412), `pending_reads` memo (:3300-3310), locked-unloaded yield (:3330-3345), rollback cleanup, FIXME :5412-5416.
**Signature:** when full with nothing spillable or evictable, the new page is admitted OVER capacity; `pending_reads` memoizes (page, disk-read Completion) pairs for reads whose cache_insert was blocked by an in-flight spill.
**Data Shape:** each Some(page_idx) mapping corresponds to a single outstanding disk read; the entry is removed exactly when the read returns Done.

### Decisive source
```text
// pager.rs:3405-3412:
// "The cache capacity is a soft limit: if nothing can be spilled or evicted,
//  the page is admitted over capacity rather than failing the read (mirroring
//  SQLite, where cache_size may be exceeded while all pages are in use); later
//  inserts drain the excess."
```

Softness is safe because of strict single-flight bookkeeping: re-entry reuses the stored pair instead of issuing a second disk read that would race the first completion writing into the same buffer. And a locked-but-unloaded cache hit YIELDS rather than returning: handing a caller such a page means "a torn / uninitialized read, or a concurrent writer filling the buffer underneath the reader" (:3330-3345). Rollback clears pending_reads so abandoned reads can't leak entries.

One honest gap documented as FIXME (:5412-5416): allocate_page hasn't implemented SQLite's 'nearby' locality parameter — freelist reuse currently fragments range scans versus same-region allocation.

**Flow:** read misses → in-flight? reuse memoized Completion : issue + memoize → cache full but unevictable → admit over capacity → later inserts drain excess.
**Invariant:** treat cache limits as pressure signals, not walls — but pair softness with single-flight bookkeeping so degradation never becomes duplication or torn reads.
**Probe:** read_page_nonblock_reentry_reuses_pending_entry asserts Arc::ptr_eq reuse of the memoized read (no-duplicate-IO invariant) plus entry removal; read_page_nonblock_inflight_cache_hit_yields_not_done plants a locked/unloaded page and asserts yield-not-done.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "pending_reads cache_insert single flight", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt soft admission with single-flight memos as a pair (either alone is unsafe); adapt capacity accounting to your pool; omit the FIXME'd nearby-allocation behavior consciously. Coverage caveat: none material.
