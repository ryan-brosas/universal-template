<!-- capsule-v2 -->
# External sorter — how does ORDER BY survive datasets that don't fit in memory?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What in-memory/spill state machine and merge discipline does Sorter implement?

## Sorter sort/next with chunk-file merge heap
**Path/Symbol:** `core/vdbe/sorter.rs:Sorter::sort` (:259), `next` (:312), `flush` (:522), `init_chunk_heap` (:420), `next_from_chunk_heap` (:474); fuzz test `fuzz_external_sort` (:1267). All starts verified unchanged at `main@d9266124f`.
**Signature:** `pub fn sort(&mut self) -> Result<IOResult<()>>`; states `SortState::{Start, Flush, InitHeap, Next}`; records live in an arena as raw pointers (`self.records: Vec<NonNull<..>>`, arena reset on flush).
**Data Shape:** in-memory phase: arena-backed record list; spill phase: one TempFile (`TempFile::with_temp_store`) holding append-only sorted chunks at `next_chunk_offset`s, each chunk read through a buffer sized `min_chunk_read_buffer_size.max(max_payload_size_in_buffer + 9)` (+9 = worst-case varint length prefix).

### Decisive source
```rust
// core/vdbe/sorter.rs::SortState::Start
if self.chunks.is_empty() {
    // Sort ascending then reverse - we pop from end so this gives ascending output.
    // NOTE: We can't just sort descending because stable sort preserves insertion
    // order for equal elements, and descending sort doesn't reverse equal elements.
    self.records.sort_by(|a, b| unsafe { a.as_ref().cmp(b.as_ref()) });
    self.records.reverse();
    self.sort_state = SortState::Next;
} else {
    self.sort_state = SortState::Flush;
}
```
```rust
// next_from_chunk_heap — pending IO gate BEFORE popping the heap
while let Some((completion, chunk_idx)) = self.pending_completion.take() {
    if !completion.succeeded() {
        self.pending_completion = Some((completion.clone(), chunk_idx));
        return Ok(IOResult::IO(IOCompletions(completion)));   // re-enter later
    }
    if let Some(c) = self.push_to_chunk_heap(chunk_idx)? { ... }
}
```

**Flow:** insert accumulates arena records until budget → flush sorts them (ascending), serializes size-varint-prefixed payloads into ONE chunk write, resets the arena. sort(): empty-chunk case sorts+reverses in place; else Flush → InitHeap (parallel group-read of every chunk's first record, checking WriteError and asserting no WaitingForWrite) → Next pops a k-way heap feeding `current`; per-chunk refill IO is carried in `pending_completion` so out-of-order reads can never surface out-of-order records.
**Invariant:** Equal keys preserve INSERTION order in final output (stability achieved via ascending-then-reverse trick because consumers pop from the end); the heap may only pop when no chunk refill is pending — popping early yields misordered rows.
**Probe:** `core/vdbe/sorter.rs::fuzz_external_sort` (:1267 — 8 seeded rounds, 1000-3000 reversed inserts force chunks, asserts output equals original order AND byte-identical records). Text anchors: `grep -c 'self.records.reverse()' core/vdbe/sorter.rs` → 2; `grep -c 'pending_completion.take()' core/vdbe/sorter.rs` → 1. Opcode consumer: `op_sorter_sort` (`core/vdbe/execute.rs:8530-8563`, increments metrics.sort_operations).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "Sorter sort flush init_chunk_heap next_from_chunk_heap", limit: 10 });
```

## Verdict
Adopt the four-state sort machine, varint-prefixed chunk format, stability trick, and pending-completion heap gate. Adapt temp-file policy to host VFS. Omit secondary-key fuzz variants (assert_secondary_key_sort :1366+) unless porting multi-key sorters.
