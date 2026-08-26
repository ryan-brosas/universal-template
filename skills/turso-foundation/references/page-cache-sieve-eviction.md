<!-- capsule-v2 -->
# PageCache SIEVE eviction — how does a clock hand with ref-bits evict under a bounded sweep, and why does the bound matter?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How do you implement second-chance eviction that is guaranteed to terminate and to make progress, without an LRU's move-to-front traffic?

## Clock/SIEVE over an intrusive list, hand-anchored insertion

**Path/Symbol:** `core/storage/page_cache.rs` — `PageCache` struct :99-113 (`clock_hand: *mut PageCacheEntry` over `queue: LinkedList<EntryAdapter>` + `map: HashMap<PageCacheKey, *mut PageCacheEntry>`), `REF_MAX = 3` :34 / `CLEAR = 0` :33, insert-after-hand MRU placement :301-319, `_delete` hand-advance-before-unlink :364-377, `evict_one` :640-706.
**Signature:** `fn evict_one(&mut self) -> Result<(), CacheError>`; helpers `advance_clock_hand` :174-197, `evictable(page)` :631-637 (clean-or-spilled ∧ ¬locked ∧ ¬pinned ∧ not page 1 ∧ `Arc::strong_count == 1`).
**Data Shape:** per-entry `ref_bit: u8` saturated at REF_MAX=3 by `bump_ref` :65; capacity soft; `evictable_count: usize` maintained incrementally as a conservative estimate.

### Decisive source
```rust
// :647-648 — the termination bound:
let mut examined = 0usize;
let max_examinations = self.len().saturating_mul(REF_MAX as usize + 1);
// loop: if evictable && ref_bit == CLEAR -> evict
//       else if evictable          -> entry.decrement_ref(); advance; examined += 1 (:693-697)
//       else                       -> advance (unevictable pages are skipped WITHOUT decrement) ; examined += 1
```
Every resident page's ref-bit can be decremented at most REF_MAX times before it reaches CLEAR, so a full sweep examines at most `len × (REF_MAX+1)` entries: after that either something was evicted or the cache genuinely cannot evict (`CacheError::Full`). Unevictable pages are passed over without burning their ref-bits — pinned/dirty pages don't get "aged" by sweeps they couldn't respond to.

**Flow:** insert places the new entry immediately AFTER the hand (circular semantics → new entry is MRU-side; first entry becomes the hand itself :301-306) → on pressure `make_room_for` loops `evict_one` until `len ≤ capacity - n` :615-628 → eviction clears loaded state and takes the page buffer (:680-681), removes from map AND intrusive queue, fixes the hand if it pointed at the removed entry.

**Invariant:** the hand must be advanced BEFORE unlinking when it points at the victim, and nulled if the advance wrapped back (:365-371 delete path, :672-676 evict path) — a dangling hand pointer into a freed intrusive entry is the classic corruption here. A cache hit only refreshes recency up to a ceiling (ref_bit ≤ 3): repeatedly-read pages resist one pass of decrement but never lock residency. Termination is arithmetic, not probabilistic — never remove the examination bound "as an optimization".

**Probe:** direct tests in `page_cache.rs`: `test_sieve_second_chance_preserves_marked_page` :1649, `test_clock_sweep_wraps_around` :1679, `test_hand_advances_on_eviction` :1729, `test_multi_level_ref_counting` :1750 (asserts `Some(REF_MAX)` ceiling). Graph confirms all four resolve in-project.

**Retrieve:**
```
echo '{"project":"turso","query":"PageCache evict_one sieve clock hand","limit":5}' | codebase-memory-mcp cli search_graph
# turso.core.storage.page_cache.PageCache.evict_one page_cache.rs 640-706
# turso.core.storage.page_cache.PageCache.advance_clock_hand page_cache.rs 174-197
```

## Verdict
Adopt bounded SIEVE for any shared read cache where LRU mutex traffic hurts; keep the exact `len × (max_ref+1)` bound and the skip-without-decrement rule for unevictables. Adapt storage to your language (the raw-pointer intrusive list is a Rust-perf choice, not part of the contract — a doubly-linked list of indices works). The pager-level admission policy that sits ON TOP of this cache is covered separately by `pager-cache-admission` / `storage-soft-cache-singleflight`.
