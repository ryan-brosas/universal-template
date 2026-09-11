<!-- capsule-v2 -->
# Pin-count page lifetime — how do you make "page evicted under a live reference" unrepresentable?

**Source:** turso (Turso) MIT `main@f1800bb8c` (re-anchored from `def9a060`); Codebase Memory `turso`. **Question:** What makes pinned-page safety a type property instead of a remembered discipline, and why counted pins rather than a flag?

## PinGuard + counted pins + clear-evicts-everything escape hatch
**Path/Symbol:** `PinGuard` `core/storage/btree.rs:398`; clone/drop contract comment (:398-430); `PageInner.pin_count: AtomicUsize` `core/storage/pager.rs:113-125` (counter rationale verbatim); double-unpin guard via fetch_update (pager.rs:883-902); `PageCache::clear` evicts-even-pinned exception (pager.rs:113-124 doc); `PageStack` slot-taking on clear (`core/storage/btree.rs:8424-8438`, `unpin_all_and_clear_slots` + Drop impl :8445).
**Signature:** `pub struct PinGuard(PageRef)` — pins on construction AND on every Clone; Drop unpins exactly once.

### Decisive source
```rust
// Since every Drop will unpin, every clone
// needs to add to the pin count
```
(btree.rs:406-407; hazard doc: any PageRef kept live across a blob operation MUST be pinned, or the pager can evict it and take its buffer out from under the still-held reference — eviction does buffer.take() REGARDLESS of live Arc<Page> refs)

And the counter rationale (pager.rs:115-120): "The reason this is a counter is that multiple nested code paths may signal that a page must not be evicted… even if an inner code path requests unpinning… the pin count will still be >0 if the outer code path has not yet requested to unpin."

**Flow:** safety regions NEST (free_page pins the freed page across a yielding state machine while allocate_page separately pins trunk/leaf pages) → a boolean flag would let an inner unpin release a page an outer path still holds → counted pins compose. Unpin uses fetch_update returning None at zero so DOUBLE-unpin is a detectable no-op. Error paths call `PageCache::clear`, which deliberately evicts EVEN PINNED pages — trading cache warmth for guaranteed pin-boundedness (pins cannot leak past a reset). PageStack takes its slots on clear too: "a leftover Some(page) after a clear could otherwise be unpinned again on the next reset."
**Invariant:** Eviction may invalidate outstanding buffer references at any yield point; the type system (PinGuard), not programmer memory, closes that hole.

**Probe:** `core/storage/pager.rs:5061 test_evict_all_unpinned_clean` evicts clean unpinned pages while a cursor holds a PageRef — the exact hazard PinGuard prevents; `:6205 read_page_exceeds_capacity_when_cache_unevictable` + `:6250 allocate_page_exceeds_capacity_when_cache_unevictable` prove reads/allocations still succeed over capacity while pins are held.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "PinGuard pin_count PageCache clear eviction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: make the safe representation a TYPE (guard object pinning per Clone), use counted pins because safety regions nest, and keep one documented bulk-clear that overrides pins on error paths. Adapt to your language's RAII equivalents; omit PageStack internals unless you port cursor stacks.
