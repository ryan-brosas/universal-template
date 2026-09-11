<!-- capsule-v2 -->
# BufferPool deferred init — why are buffers handed out before the arena exists, and what does an allocation do when the pool isn't ready or is full?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How does a static pool whose slot size depends on a not-yet-read file header serve allocations from process start without ever reallocating or fragmenting its arenas?

## Two-phase lifecycle: temp-buffer phase → OnceLock-guarded arena init

**Path/Symbol:** `core/storage/buffer_pool.rs` — `BufferPool::begin_init` :192-200, `finalize_with_page_size` :205-229, `PoolInner::allocate` fallback ladder :243-262, `get_db_page_buffer`/`get_wal_frame_buffer` :264-278, `db_page_size: OnceLock<usize>` :113, TEMP_BUFFER_CACHE reinit :208-214.
**Signature:** `begin_init(io: &Arc<dyn IO>, arena_size: usize) -> Arc<Self>` (stores only the IO handle, no arenas); `finalize_with_page_size(&self, page_size: usize) -> Result<()>` (idempotent; creates arenas exactly once).
**Data Shape:** `PoolInner { io: Option<Arc<dyn IO>>, page_arena: Option<Arc<Arena>>, wal_frame_arena: Option<Arc<Arena>>, arena_size: usize, db_page_size: OnceLock<usize> }`.

### Decisive source
```rust
// :220-227 — the OnceLock IS the concurrency guard for arena creation:
// Tries to atomically (guarenteed by the OnceLock) initialize the page size for the inner pool.
// If it succeeds, we now have to initialize the arenas.
// If the initialization fails, this means the arenas have already been initialized by a previous thread
// This avoids a potential TOCTOU race, where 2 threads could try to initalize the arena at the same time
if inner.db_page_size.set(page_size).is_ok() {
    inner.init_arenas()?;
};
```
Before finalize, "the pool will use temporary buffers which are cached in thread local storage" (:202-204). If the real page size differs from `DEFAULT_PAGE_SIZE` (4096), those temp buffers are the WRONG SIZE — so finalize first calls `TEMP_BUFFER_CACHE … reinit_cache(page_size)` (:208-214) so stale-sized cached buffers are never reused for other operations.

**Flow:** begin_init captures io → header reads get thread-local temp buffers → page size lands → finalize: reinit temp cache if non-default size → `OnceLock::set` wins exactly one thread → that thread builds both arenas (`init_arenas` :281-327) → from then on `allocate(len)` routes by size: `len == db_page_size + WAL_FRAME_HEADER_SIZE` → WAL arena; everything else ≤ slot_size → page arena; **arena miss or oversize → `Buffer::new_temporary(len)` heap fallback** (:250-261, `Arena::try_alloc` returns None for size > slot_size :408-413).

**Invariant:** arenas are created AT MOST ONCE per process and never resized — the OnceLock-set-wins check replaces any lock around arena construction. Every allocation path must degrade to a correct temporary buffer rather than fail: pool exhaustion is a performance cliff (io_uring registered fast paths lost), never an error. Pooled buffers occupy EXACTLY ONE slot (asserted on free :428-439); multi-slot requests silently fall through to temporary heap buffers.

**Probe:** shuttle tests pin the concurrency envelope this design exists to satisfy: `shuttle_concurrent_finalize` :693 (racing finalizers create one arena set), `shuttle_arena_exhaustion_and_recovery` :977 (temporary fallback keeps allocation live after exhaustion), `shuttle_alloc_during_drop_slot_recycling` :852 (slot recycle under concurrent drop). No cargo runner in the inspo clone — verified by direct source inspection at `def9a060`; coverage caveat: runtime RED/GREEN not executed here.

**Retrieve:**
```
echo '{"project":"turso","query":"BufferPool finalize_with_page_size Arena try_alloc","limit":4}' | codebase-memory-mcp cli search_graph
# turso.core.storage.buffer_pool.BufferPool.finalize_with_page_size buffer_pool.rs 205-229
# turso.core.storage.buffer_pool.Arena.try_alloc buffer_pool.rs 408-425
```

## Verdict
Adopt the deferred-init lifecycle verbatim for any pool whose slot geometry depends on late-arriving file metadata; adopt the OnceLock-set-wins guard instead of a mutex around one-shot construction. Adapt the temp-cache reinit to your thread-local scheme (or skip if your temps are size-agnostic). The sibling capsule `buffer-pool-arena-split` covers WHY there are twin arenas and how io_uring registration IDs leak into buffers — read both before porting.
