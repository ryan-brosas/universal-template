<!-- capsule-v2 -->
# PageCache spill & soft-capacity accounting — when does the cache order dirty pages flushed, and how is O(1) "can I evict?" bookkeeping kept honest?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How does the cache decide to spill dirty pages BEFORE eviction pressure, and how does it answer "is there room" without scanning?

## Threshold-triggered spill selection + incrementally-maintained evictable count

**Path/Symbol:** `core/storage/page_cache.rs` — `spill_threshold = capacity × DEFAULT_SPILL_THRESHOLD_PERCENT (90)` :27/:159, recomputed on resize with `.max(1)` :451; `needs_spill` fast/slow path :458-480; `spillable(page)` :506-514; `collect_spillable_pages` :568-587; `check_spill(max_pages) -> SpillResult::{NotNeeded, PagesToSpill(Vec<PinGuard>), CacheFull}` :591-602; `notify_page_dirty`/`notify_page_spilled` counter maintenance :532-558; `force_insert_page`/`force_upsert_page` over-capacity admission :221-251; self-healing `get` :414-421.
**Signature:** `pub fn check_spill(&self, max_pages: usize) -> SpillResult`; `pub fn force_insert_page(&mut self, key, value) -> Result<(), CacheError>` (on `CacheError::Full` re-inserts with `bypass_capacity=true`).
**Data Shape:** `SpillResult::PagesToSpill` carries `Vec<PinGuard>` — candidates pinned during collection so they can't vanish before the caller writes them.

### Decisive source
```rust
// :466-479 — the O(1)-then-scan decision:
// Fast path: use tracked evictable_count to avoid O(n) scan:
//   evictable_count is a conservative upper bound on evictable pages,
//   Empty slots also count as available room since make_room_for uses them first.
let empty_slots = self.capacity.saturating_sub(len);
let available_room = self.evictable_count.saturating_add(empty_slots);
if available_room >= needed_evictable { return false; }
// Slow path: do the full count since our estimate suggests we might need to spill.
self.count_evictable_pages() < needed_evictable
```
The counter is a CONSERVATIVE UPPER BOUND: `counted_as_evictable` (:520-527) ignores locked/pinned/strong-count (short-lived states) and tracks only dirty-vs-spilled, so it may overcount but never undercount. If even the optimistic bound says there isn't room, only then pay the O(n) exact scan. Spill candidates are sorted by page id (`spillable.sort_by_key(|pg| pg.get().id)` :585) — deterministic write order for better disk locality — and page 1 (`DatabaseHeader::PAGE_ID`) plus pages with non-empty `overflow_cells` are never spillable.

**Flow:** inserts push len past 90% → caller asks `check_spill` → fast-path bound says tight → collect ≤max_pages spillable as PinGuards, id-ordered → pager flushes them; on flush completion `notify_page_spilled` bumps `evictable_count` back up (dirty→spilled = evictable again). When insert finds EVERYTHING unevictable, `force_insert_page` admits over capacity rather than failing a read that can't be undone — SQLite semantics, later inserts drain the excess (:232-241 doc). `get()` heals aborted reads: a cached-but-unloaded-and-unlocked page (read completion aborted by one statement) is deleted on sight because "page cache is not per Statement" and would poison the next statement (:414-417).

**Invariant:** the tracked counter must be updated at EVERY dirty/spilled transition via the notify methods — forgetting one transition silently converts the bound into an undercount, and then `needs_spill` lies in the dangerous direction (says "room exists" when it doesn't). Force-admission is for pages whose allocation already happened: refusing them wastes memory AND fails work.

**Probe:** direct tests in `page_cache.rs`: `test_evictable_count_tracking` :1803, `test_needs_spill_fast_path` :1840, `test_force_insert_allows_temporary_over_capacity_cache` :1114, `test_force_upsert_allows_temporary_over_capacity_cache` :1151, `test_make_room_for_with_dirty_pages` :1094. Verified by source inspection at `def9a060`; no cargo runner in this clone.

**Retrieve:**
```
echo '{"project":"turso","query":"PageCache needs_spill check_spill spillable","limit":6}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt threshold-triggered spill with PinGuard candidate handoff and id-ordered batches; adopt conservative-bound + exact-fallback counting wherever "should I do expensive cleanup?" is asked per operation. Adapt the 90% constant to workload; keep `.max(1)` guards for tiny caches. The write-back side of spilling (TAG_WRITE_PENDING sentinels) lives in `pager-spill-tags` / `storage-spill-tags`.
