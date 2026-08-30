<!-- capsule-v2 -->
# BufferPoolReservation — how do you make memory reservations exception-safe with RAII only?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How are pool charges tied to object lifetime so failed allocations can never leak accounting?

## Non-copyable reservation; move zeroes the source; destructor asserts zero
**Path/Symbol:** `src/include/duckdb/storage/buffer/buffer_pool_reservation.hpp:BufferPoolReservation` (:20-37) + `TempBufferPoolReservation` (:39-46); impl `src/storage/buffer/buffer_pool_reservation.cpp`.
**Signature:** `void Resize(idx_t new_size)` → `pool.UpdateUsedMemory(tag, new_size - size)`; `void Merge(BufferPoolReservation src)`; move-assign re-charges `pool.UpdateUsedMemory(tag, -old_size)` then adopts src's charge.
**Data Shape:** `{MemoryTag tag; idx_t size{0}; BufferPool &pool;}` — copy ctor/assign `= delete`; `~BufferPoolReservation()` has `D_ASSERT(size == 0)` (charge must already be released via Resize/move).

### Decisive source
```cpp
BufferPoolReservation &BufferPoolReservation::operator=(BufferPoolReservation &&src) noexcept {
    pool.UpdateUsedMemory(tag, -UnsafeNumericCast<int64_t>(size)); // release mine
    tag = src.tag; size = src.size;
    src.size = 0;                                                  // neutralize source
    return *this;
}
void BufferPoolReservation::Resize(idx_t new_size) {
    auto delta = UnsafeNumericCast<int64_t>(new_size) - UnsafeNumericCast<int64_t>(size);
    pool.UpdateUsedMemory(tag, delta);
    size = new_size;
}
// TempBufferPoolReservation dtor: Resize(0) — RAII release
```

**Flow:** construct (zero) → Resize charges deltas through the pool → Merge folds a temporary into this one by summing sizes and zeroing the source → destruction releases anything left.
**Invariant:** the recorded `size` is the ONLY truth — every transition must pass through Resize/move so `UpdateUsedMemory` sees balanced deltas; the base destructor asserting `size == 0` catches double-release bugs in debug builds.
**Probe:** `grep -c 'BufferPoolReservation(const BufferPoolReservation &) = delete' src/include/duckdb/storage/buffer/buffer_pool_reservation.hpp` → `1`; `grep -c 'src.size = 0' src/storage/buffer/buffer_pool_reservation.cpp` → `3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "BufferPoolReservation TempBufferPoolReservation Resize Merge UpdateUsedMemory", limit: 10 });
```

## Verdict
Adopt delete-copy + move-neutralize + assert-on-destruct as the canonical charge token; adapt tag typing; nothing DuckDB-specific remains once the pool callback is yours.
