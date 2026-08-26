<!-- capsule-v2 -->
# Soft-limit page cache + single-flight reads — how do you degrade under pressure without torn reads or duplicate IO?

**Source:** turso (Turso) MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** When can a page cache admit over capacity, and what bookkeeping keeps degradation safe?

## Advisory capacity + memoized in-flight disk reads + yield-on-locked-hit
**Path/Symbol:** `core/storage/pager.rs` soft-limit doc (:3405-3415, restated :4067-4068, test doc :6200); `pending_reads` map (:1363, entry contract :3317, re-entry resume :1458/:1834); locked-but-unloaded hit yields (:6672 region); FIXME 'nearby' allocation locality gap (:5412-5416).
**Data Shape:** `pending_reads: RwLock<HashMap<i64, PendingRead>>` memoizes (page → disk-read Completion) pairs for reads whose cache_insert was blocked by an in-flight spill.

### Decisive source
```rust
/// The cache capacity is a soft limit: if nothing can be spilled or
/// evicted, the page is admitted over capacity rather than failing the
```
(pager.rs:3408-3409, continuing "…the read (mirroring SQLite, where cache_size may be exceeded while all pages are in use); later inserts drain the excess.")

**Flow:** cache full & nothing evictable/spillable → admit OVER capacity (softness mirrors SQLite cache_size semantics) → safety rests on strict single-flight bookkeeping: "Each Some(page_idx) mapping corresponds to a single outstanding disk read; the entry is removed exactly when this method returns Done" (:3317) — re-entry reuses the stored pair instead of issuing a second disk read that would race the first completion writing into the same buffer. A locked-but-unloaded cache hit YIELDS rather than returning the page: handing it over means "a caller reads a torn / uninitialized buffer, or races a writer filling" it (:6672). Rollback clears pending_reads so abandoned reads cannot leak entries.
**Invariant:** Softness is safe ONLY with single-flight dedup — degradation must never become duplication or torn reads.

**Probe:** `read_page_nonblock_reentry_reuses_pending_entry` (pager.rs:6612) asserts Arc::ptr_eq reuse of the memoized read plus entry removal (no-duplicate-IO); `read_page_nonblock_inflight_cache_hit_yields_not_done` (:6675) plants a locked/unloaded page and asserts yield-not-done.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "pending_reads soft limit admit over capacity single flight", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt soft capacity + pending-read memoization as an inseparable pair; adopt yield-not-done on locked hits. Adapt container types; record the same honest FIXME if you skip allocation-locality ('nearby') on first port.
