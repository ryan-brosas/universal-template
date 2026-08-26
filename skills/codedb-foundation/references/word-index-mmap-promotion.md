<!-- capsule-v2 -->
# WordIndex mmap zero-copy ↔ heap promotion — when does a read-only index pay materialization?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How does an inverted word index serve queries with ~zero RSS yet accept writes without a full rebuild?

## Zero-copy index with lazy heap promotion
**Path/Symbol:** `src/index.zig:WordIndex` (`mmap_data`/`word_dir` fields :36–43, `mmapSearch` :453–474, `promoteIfBorrowed` :479–518, `removeFile` guard :129–142).
**Signature:** `fn promoteIfBorrowed(self: *WordIndex) !void`; `fn mmapSearch(self: *WordIndex, lower: []const u8) []align(1) const WordHit`.
**Data Shape:** In zero-copy mode `mmap_data` holds the mmap'd `word.index` bytes and `index`/`path_to_id`/`file_words` are EMPTY; only `id_to_path` (duped paths), `word_dir` ([]u32 offsets of each sorted word record), and `doc_lengths` are heap-resident. Postings records are `[u16 word_len][word][u32 hit_count][WordHit{doc_id,line_num} × count]` at arbitrary byte offsets, hence `align(1)` slices read via unaligned loads.

### Decisive source
```zig
// First write to a zero-copy (mmap) index rebuilds a heap index from the
// mmap so the mutation has somewhere to land, then unmaps.
fn promoteIfBorrowed(self: *WordIndex) !void {
    const data = self.mmap_data orelse return;
    ... // build new StringHashMap from every word_dir record, duping keys,
        // appendUnalignedSlice for postings; then commit:
    self.index.deinit(); self.path_to_id.deinit();
    self.allocator.free(self.word_dir); cio.munmap(data);
    self.index = new_index; self.mmap_data = null;
```
and the write-side guard:
```zig
pub fn removeFile(self: *WordIndex, path: []const u8) void {
    if (self.mmap_data != null) {
        var tracked = false;
        for (self.id_to_path.items) |p| { if (std.mem.eql(u8, p, path)) { tracked = true; break; } }
        if (!tracked) return;              // no-op for untracked paths
        self.promoteIfBorrowed() catch return;   // a remove is a WRITE
    }
```

**Flow:** `mmapFromDisk` builds word_dir by scanning records sequentially (no postings copy) → all reads (`search`, `searchPrefix` lower-bound binary search) hit the mmap zero-copy → the FIRST mutating call (`indexFile`→`promoteIfBorrowed` at :279, or `removeFile`) checks tracked-ness, materializes a full heap index, munmaps, and clears `mmap_data` → subsequent operations are pure heap ops.
**Invariant:** Reads never mutate state (a warm daemon searching stays at small RSS); exactly ONE promotion happens per load, paid only by an actual edit. `promoteIfBorrowed` failure must leave the old mmap intact (errdefer frees the half-built heap maps). `searchPrefix` on mmap mode must skip keys `<= prefix.len` (exact match is Tier 0's job).
**Probe:** `src/test_index.zig` bm25-persistence round-trip pins disk layout; `grep -n "promoteIfBorrowed" src/index.zig` shows all three call sites (:141, :279, plus definition) — any new write path must call it first.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", query: "promoteIfBorrowed", limit: 10 });
```

## Verdict
Adopt the mode lattice (read-only mmap view / mutable heap index) and the promote-on-first-write rule for any large immutable inverted index that must accept occasional edits; adapt record framing (u16 len prefixes, little-endian) to your host format; omit the Windows/POSIX mmap shims in `cio.zig`.
