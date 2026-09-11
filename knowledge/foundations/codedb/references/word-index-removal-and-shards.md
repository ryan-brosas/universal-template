<!-- capsule-v2 -->
# WordIndex removal dual-path + shard-merge id parity — how do bulk-loaded docs get deleted, and why does merged order reproduce serial ids?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** What must a porter replicate so re-index/remove works for files indexed WITHOUT per-file term sets, and so parallel indexing yields identical doc_id assignment to serial indexing?

## Removal: tracked fast path vs bulk sweep
**Path/Symbol:** `src/index.zig:WordIndex.removeFile` :127–235; `getOrCreateDocId` free-slot reuse :50–67; `indexOneToken` failed-dupe rollback :236–255.
**Data Shape:** `file_words: path → []const []const u8` (per-file contributed words) exists only for incrementally indexed files; bulk/mmap/shard paths set `skip_file_words=true` and own their path strings (`owns_id_paths=true`). Freed doc slots go to `free_ids` and `id_to_path[slot] = ""` tombstone.

### Decisive source
```zig
// No per-file word list: the file came from a bulk path ... where removeFile
// used to be a silent no-op that left every stale posting behind. Sweep all
// posting lists for the doc_id instead; the next indexFile gives the file a
// word list, so this runs at most once per file.
const doc_id = self.path_to_id.get(path) orelse return;
_ = self.path_to_id.remove(path);
...
var empty_words: std.ArrayList([]const u8) = .empty;
var it = self.index.iterator();
while (it.next()) |entry| {
    const hits = entry.value_ptr;
    var i: usize = 0;
    while (i < hits.items.len) {
        if (hits.items[i].doc_id == doc_id) _ = hits.swapRemove(i) else i += 1;
    }
    if (hits.items.len == 0) empty_words.append(...) catch continue;
}
for (empty_words.items) |word| { ... fetchRemove, deinit, free key ... }
```
Failed-dupe rollback (the key points at the tokenizer's stack buffer):
```zig
const duped = self.allocator.dupe(u8, token) catch |err| {
    _ = self.index.remove(token);   // a failed dupe must take the fresh entry
    return err;
};
gop.key_ptr.* = duped;
```

**Flow:** `removeFile` → tracked path: pop `file_words`, walk its words, swapRemove matching doc_ids, prune empty buckets → bulk path: one full index sweep filtering doc_id (at most once per file; next `indexFile` installs a word list). `getOrCreateDocId` prefers `free_ids` (put BEFORE pop so a failed put leaves both untouched); `indexFile` always calls `removeFile` first, making re-index = remove + insert.
**Invariant:** A posting bucket is pruned the moment it empties (churn never leaks key/list entries); `total_tokens` is adjusted with wrapping sub/add symmetrically on remove and re-index; duplicate `(doc_id,line)` hits collapse because `indexOneToken` compares the LAST element before appending.
**Probe:** `src/test_index.zig` ("bm25-state-sync: re-index and remove update total_tokens correctly") pins the accounting; `src/adversarial_tests.zig` "adversarial: indexFile then removeFile leaves clean state".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "mergeShard", limit: 10 });
```

## Shard merge reproduces serial doc-id assignment
**Path/Symbol:** `src/index.zig:WordIndex.mergeShard` :382–435 (twin: `TrigramIndex.mergeBulkShard` :1480–1518).
**Flow:** Workers build shards over disjoint contiguous document ranges with LOCAL ids starting at 0 → merge offsets each shard by `base = current global doc count` → merging shards in worker/source order reproduces EXACTLY the serial single-worker doc_id numbering. Paths/terms are re-duped into the target allocator (shard arena dies after merge); postings stay doc_id-ascending because each shard's global range follows the previous one.
**Invariant:** Every allocation step carries a transactional errdefer that rolls back the PREVIOUS map insertion (the old ordering freed `duped` after a later failure while `id_to_path` still referenced it → dangling pointer/double-free). `TrigramIndex.mergeBulkShard` additionally asserts `owns_paths && free_ids empty` on both sides and moves posting lists wholesale when allocators match (`can_transfer`).
**Probe:** `grep -c "errdefer" src/index.zig` ≥ 12; `src/test_index.zig` covers decompose/bloom/bulk builders — cite `bm25-persistence: writeToDisk/readFromDisk preserves total_tokens and doc_lengths` (:3072) for the persisted accounting that merges feed.

## Verdict
Adopt the two removal regimes + offset-based shard merge with worker-order parity (it makes parallel indexing bit-compatible with serial snapshots); adapt the arena lifetime rules to your allocator; omit the Zig-specific errdefer idioms while KEEPING the rollback ordering they express.
