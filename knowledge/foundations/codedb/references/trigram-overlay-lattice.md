<!-- capsule-v2 -->
# AnyTrigramIndex overlay lattice — why does an mmap index promote to base+overlay instead of materializing, and how is a remove expressed on immutable data?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How does a zero-copy disk index accept incremental edits without paying a full heap load?

## heap / mmap / mmap_overlay three-state union
**Path/Symbol:** `src/index.zig:AnyTrigramIndex` :2541–2798 (`MmapOverlay` :2546–2572, `indexFile` promotion :2657–2677, `removeFile` :2679–2699, `mergeOverlayCandidates` :2597–2634, `materializeOverlay` :2720–2757).
**Signature:** `pub const AnyTrigramIndex = union(enum) { heap: TrigramIndex, mmap: MmapTrigramIndex, mmap_overlay: MmapOverlay }`.
**Data Shape:** Overlay = `{base: MmapTrigramIndex (untouched), overlay: TrigramIndex (heap, receives ALL writes), masked: StringHashMap(void) (paths whose base entries are superseded or removed; owns keys), masked_in_base: u32}`.

### Decisive source
```zig
.mmap => |*m| {
    // Promote to mmap_overlay: keep mmap base, add heap overlay
    const base = self.mmap;
    self.* = .{ .mmap_overlay = .{ .base = base,
        .overlay = TrigramIndex.init(alloc),
        .masked = std.StringHashMap(void).init(alloc) } };
    try self.mmap_overlay.overlay.indexFile(path, content);
    self.mmap_overlay.mask(path);
},
...
// A remove is a write: promote so the base entry can be masked.
if (!m.containsFile(path)) return;
```
Candidate merge drops masked base paths:
```zig
fn mergeOverlayCandidates(mo, base, over, allocator) ?[]const []const u8 {
    for (base.?) |p| { if (mo.masked.contains(p)) continue; merged.put(p, {}) ... }
```
Persist re-materializes and rewrites in place:
```zig
/// ... writing over the very directory the live base is mmapped from is safe
/// — the mapping keeps the old inode alive.
fn materializeOverlay(mo: *const MmapOverlay) !TrigramIndex  // base minus masked + overlay
```

**Flow:** load → `.mmap` (zero-copy candidates via lookup binary search) → first write/remove promotes to `.mmap_overlay` keeping the base mmapped → every subsequent edit lands in the overlay heap index and masks the path (mask() is idempotent and counts `masked_in_base`) → queries = merge(base.candidates minus masked ∪ overlay.candidates) → persist = materialize merged heap view and serialize with the tmp+rename writer (old inode stays alive under the open mapping).
**Invariant:** The BASE is never mutated — correctness lives entirely in the mask set; `fileCount()` = base + overlay − masked_in_base (double-count correction); a path must be masked even when only removed from the overlay side; alloc-failure inside merge returns null so callers fall back to full scan (never a wrong answer).
**Probe:** `src/test_index.zig` bulk/bloom suites cover heap behavior; mechanical probe: `grep -n "masked_in_base" src/index.zig` shows exactly the fileCount correction sites; adversarial suite's "re-indexing same file replaces old data" pins replace semantics through any state.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "AnyTrigramIndex", limit: 10 });
```

## Verdict
Adopt base+overlay-with-mask-set as the standard answer for read-optimized persistent indexes needing incremental updates (same shape as LSM memtables); adapt materialization timing to your persistence cadence; omit Zig union-tag mechanics.
