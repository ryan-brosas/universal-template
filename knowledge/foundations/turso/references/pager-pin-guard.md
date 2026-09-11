<!-- capsule-v2 -->
# Page pinning & eviction — how do you make "held page got evicted under me" unrepresentable?

**Source:** turso (MIT) @ main`f1800bb8c` (re-anchored from `def9a060`); Codebase Memory `turso`. **Question:** When cache eviction can invalidate outstanding references, what type-level and count-level discipline prevents use-after-evict?

## PinGuard + counted pins (not flags)
**Path/Symbol:** `core/storage/btree.rs:915-925` (PinGuard rationale), clone-pins rule (:398-430); `core/storage/pager.rs` unpin (:883+), deliberate `PageCache::clear` exception (`core/storage/pager.rs:113-124` doc on `PageInner.pin_count`), PageStack slot-taking `unpin_all_and_clear_slots` (:8424-8438).
**Signature:** Pages carry an AtomicUsize pin count; pin > 0 makes a page ineligible for cache eviction. PinGuard pins on construction AND on every Clone ("Since every Drop will unpin, every clone needs to add to the pin count"); unpin uses fetch_update returning None at zero so double-unpin is a detectable no-op.
**Data Shape:** counted pins, not boolean flags, because safety regions NEST: free_page pins the freed page across a state machine that may yield while allocate_page separately pins trunk/leaf pages — a flag would let an inner unpin release a page an outer path still holds.

### Decisive source
```text
// btree.rs:915-925:
// "any PageRef kept live across a blob operation MUST be pinned, or the pager
//  can evict it and take its buffer out from under the still-held reference
//  (eviction does buffer.take() regardless of live Arc<Page> refs). Storing a
//  PinGuard … makes an unpinned held page unrepresentable rather than a
//  discipline to remember."
```

One deliberate exception is documented at pager.rs:113-124: `PageCache::clear` evicts even pinned pages — error paths always clear the cache, trading warmth for guaranteed pin-boundedness (pins can't leak past a reset). PageStack takes its slots on clear for the same reason (:8424-8438): "a leftover `Some(page)` after a clear could otherwise be unpinned again on the next reset, decrementing the pin count of a page another cursor's stack still relies on."

**Flow:** cursor enters pin-requiring region → constructs PinGuard (count++) → clones propagate counts → drops decrement; eviction skips pinned; error path clears everything including pinned.
**Invariant:** make the safe representation a TYPE, not a convention — and use counted pins because safety regions nest.
**Probe:** pager tests `read_page_exceeds_capacity_when_cache_unevictable` (pager.rs:6205) + `allocate_page_exceeds_capacity_when_cache_unevictable` (:6250) hold strong refs (pins) on all resident pages and prove reads/allocations still succeed by admitting over capacity, draining once refs drop; `test_evict_all_unpinned_clean` (pager.rs:5061 → page_cache.rs:398) evicts clean unpinned pages while a cursor holds a PageRef — the exact hazard PinGuard prevents.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "PinGuard pin_count evict", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the guard-type pattern anywhere eviction can take buffers from live refs; adapt RAII mechanics to your language; omit the clear-everything escape if your error paths can tolerate leaked pins. Coverage caveat: none material.
