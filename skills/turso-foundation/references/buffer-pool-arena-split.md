<!-- capsule-v2 -->
# BufferPool arena — why does the WAL frame buffer share the page arena's slot size, and what does io_uring change?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How are fixed-size I/O buffers pooled so io_uring registered buffers work and page/frame allocations never fragment each other?

## Two same-slot arenas + registration-aware buffer IDs
**Path/Symbol:** `core/storage/buffer_pool.rs:96-118` (`PoolInner`: `page_arena`, `wal_frame_arena`, `db_page_size: OnceLock`), slot math :358-365, two-phase init :192-205 (`begin_init`/`finalize_with_page_size`), `ArenaBuffer::fixed_id` :47-54.
**Signature:** `pub fn begin_init(io: &Arc<dyn IO>, arena_size: usize) -> Arc<Self>` → `finalize_with_page_size(&self, page_size)`; accessors `get_page()` / `get_wal_frame()` return `Buffer`.
**Data Shape:** WAL arena slots are `db_page_size + WAL_FRAME_HEADER_SIZE (24)` — "preventing the fragmentation or complex book-keeping needed to use the same arena for both sizes". Arena IDs ≤ `UNREGISTERED_START` mean NOT io_uring-registered; registered arenas occupy ring indices 0..=1.

### Decisive source
```rust
// :104-107 — the split rationale:
/// An Arena which returns `ArenaBuffer`s of size `db_page_size`
/// plus 24 byte `WAL_FRAME_HEADER_SIZE`, preventing the fragmentation
/// or complex book-keeping needed to use the same arena for both sizes.
// :47-50 — registration leak-through:
/// Returns the `id` of the underlying arena, only if it was registered with `io_uring`
```
Two-phase init exists because the page size isn't known until the header is read: arenas are created eagerly with a byte budget, then finalized once `db_page_size` lands. `ArenaBuffer` carries `(arena: Arc, ptr, arena_id, slot_idx, len)` and its `Drop` returns exactly one slot (`arena.free(self.slot_idx, self.logical_len())`) — logical length may be < slot size but never occupies more than one slot for pooled buffers.

**Flow:** begin_init (io captured) → first header read → finalize_with_page_size fixes slot sizes & registers fixed buffers with the ring → get_page/get_wal_frame hand out ArenaBuffers whose fixed_id feeds io_uring's registered-buffer fast path.
**Invariant:** never allocate a frame from the page arena (or vice versa): equal-count pools with different slot semantics beat one general pool; buffer lifetime must not outlive the arena Arc (Drop co-owns it).
**Probe:** module tests in `buffer_pool.rs` cover pool init/registration paths; pager-level pressure tests (`read_page_exceeds_capacity_when_cache_unevictable` in pager.rs) exercise buffers under over-capacity admission.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "BufferPool wal_frame_arena fixed_id Arena", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt twin-arena pooling for any async-I/O engine using registered buffers; adapt slot arithmetic to your frame format (keep the +header trick). Omit io_uring registration on backends without it — fixed_id degrades to None cleanly.
