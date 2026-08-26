<!-- capsule-v2 -->
# B-tree minimum cell size padding — why can a 3-byte index cell corrupt a page?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** When a cell is smaller than the page's minimum cell size, what must the writer pad, and what must balancing strip, so the content area never slides into the pointer array?

## The MINIMUM_CELL_SIZE duality: leaf cells are padded, dividers are real-size
**Path/Symbol:** `MINIMUM_CELL_SIZE: usize = 4` (`core/storage/sqlite3_ondisk.rs:81`), `LEFT_CHILD_PTR_SIZE_BYTES = 4` (:86); write side `core/storage/btree.rs`: `fn ensure_min_cell_size` (:8138-8142), free-space check `payload.len().max(MINIMUM_CELL_SIZE) + CELL_PTR_SIZE_BYTES <= free` (:9538), overflow-pad on IndexLeaf (:9549-9552), divider re-pad when copying back to a leaf (:3730-3737), promote-time strip `real_len < MINIMUM_CELL_SIZE` assert :4289; reader side `core/storage/pager.rs::_cell_get_raw_region_faster` IndexLeaf clamp (:631-636) and TableLeaf clamp (:651-657); debug validator `debug_validate_cells_core` overlap asserts (:9477-9490); direct test `test_tiny_cell_insert_must_not_overlap_cell_pointer_array` (btree.rs:12870-12903).
**Signature:** `fn ensure_min_cell_size(buf: &mut Vec<u8>, cell_start: usize)` — zero-fills until `cell_start + MINIMUM_CELL_SIZE`, saturating.
**Data Shape:** only INDEX cells can be sub-minimum: a record of `0|1|''|X''` serializes to 2 bytes ⇒ 3-byte cell. Table leaf cells always carry a rowid varint keeping them ≥4. The record's own length prefix makes padding invisible to readers.

### Decisive source
```rust
// core/storage/btree.rs:9534-9538 — reserve the minimum even for tiny payloads,
// else allocation (which takes ≥MINIMUM_CELL_SIZE) overruns the reservation:
//   // allocate_cell_space() never allocates less than MINIMUM_CELL_SIZE
//   // bytes, so a smaller payload must reserve that much or the cell
//   // content area slides into the cell pointer array.
//   payload.len().max(MINIMUM_CELL_SIZE) + CELL_PTR_SIZE_BYTES <= free
// :3730-3732 — dividers store the REAL size after the child pointer...
//   // The divider holds the leaf cell's real size after its child pointer;
//   // back on a leaf the cell takes the minimum size again.
// :4289 — ...so stripping must be provably padding-only:
//   turso_assert!(real_len < MINIMUM_CELL_SIZE,
//     "only cells below the minimum cell size carry padding", ...)
```

**Flow:** insert checks `max(payload, 4) + 2 ≤ free` → too big ⇒ overflow path pads IndexLeaf payloads to 4 so balancing sees ONE size everywhere → balance copies a divider back down to a leaf: re-pad after the child pointer (:3733) → balance promotes a leaf cell into a divider: read the real length from the record's own varint prefix and truncate the padding before writing the parent cell (:4282-4295) → debug builds additionally assert content-area ≥ pointer-array-end on every validated page (:9479-9490).
**Invariant:** a leaf cell ALWAYS occupies ≥4 bytes on its page (reader `cell_get_raw_region` reports the padded size); a divider in the parent stores the cell's REAL size after its child pointer. Forgetting either half corrupts: skipping the reservation lets a 3+2 check pass a 6-byte allocation (exactly the pinned test's 5-free-bytes scenario); skipping the strip duplicates padding bytes into the parent divider.
**Probe:** from repo root: `cargo test -p turso_core --lib -- test_tiny_cell_insert_must_not_overlap_cell_pointer_array` → 1 passed (executed GREEN at this pin). Text anchors: `grep -c 'only cells below the minimum cell size carry padding' core/storage/btree.rs` → 1; `grep -c 'payload.len().max(MINIMUM_CELL_SIZE)' core/storage/btree.rs` → 3 (two `cell_size` sites :8889/:8958 + free-space check).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "ensure_min_cell_size", limit: 5 });
```
(rank-1 resolves `core.storage.btree.ensure_min_cell_size core/storage/btree.rs 8138-8142`, line-exact at this pin)

## Verdict
Adopt the padded-leaf/real-divider duality plus the max() reservation verbatim whenever your page format has a minimum cell size; adapt the constant to your freeblock-header needs; omit the TableLeaf clamps if your rowids guarantee ≥4-byte cells. Coverage caveat: none material.
