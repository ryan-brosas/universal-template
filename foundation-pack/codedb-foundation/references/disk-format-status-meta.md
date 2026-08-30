<!-- capsule-v2 -->
# Two-file trigram persistence format + header-only status reads — what does OOM-proof lazy loading look like, and which counts must NEVER force a full index load?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How are postings persisted for both heap reload AND direct mmap, and why does `status` refuse to build anything?

## Contiguous-postings + offset-table dual-consumable layout
**Path/Symbol:** `src/index.zig` (`writeToDisk` :1750–1909 two-file v3, `DiskPosting` extern :1727–1732, `LookupEntry` :1741–1746, `MmapTrigramIndex.initFromDisk` :2161–2260, `readStatusMeta` :2125–2143).
**Signature:** postings file = `CDBT` magic + u16 version + u32 file_count + git-head block (51B header) + `[u16 len][path]×N` file table + raw `DiskPosting{file_id u32, next_mask u8, loc_mask u8, pad 2}` records; lookup file = `CDBL` + u16 version + pad + u32 count + `[LookupEntry{trigram u32, offset u32, count u32}]×T`.
**Data Shape:** In-memory doc_ids are remapped to DENSE disk ids by walking `id_to_path` in ascending order — because posting lists are doc_id-sorted, remapped disk ids stay sorted, which the mmap binary searches require.

### Decisive source
```zig
// Step 1: Build the file table in ascending in-memory doc_id order. Posting
// lists are sorted by doc_id, so this makes their remapped disk file_ids
// sorted too — an invariant required by the mmap merge and binary searches.
// Each file is replaced via tmp + rename; publishing the pair is not transactional.
// #553: CLI `status` used to materialize the whole index ... leaked a multi-GB
// resident orphan that stacked to OOM.
pub fn readStatusMeta(io, data_dir, allocator) StatusMeta {
    const hdr = TrigramIndex.readDiskHeader(...) orelse return .{ .indexed = false, ... };
    return .{ .indexed = true, .file_count = hdr.file_count, .git_head = hdr.git_head };
}
```
Loader hardening (both heap and mmap readers): magic+version gates, `pos != data.len ⇒ null`, `dl_count != file_count ⇒ null`, per-entry bounds checks before every read, pre-sized hash maps (`ensureTotalCapacity(word_count)` saves tens of MB of doubling).

**Flow:** serialize postings contiguously in sorted-trigram order while streaming LookupEntry offsets in fixed 4096 batches → rename each file independently over its final name → consumers choose: heap reader rebuilds maps (validating every offset/count against totals), mmap reader keeps ONLY a small word_dir-equivalent (lookup entries scanned in place, postings read on demand), header-only readers (`readDiskHeader`, `readGitHead`, `readStatusMeta`) touch just the first 51 bytes.
**Invariant:** Versioned headers with strict upper-bound acceptance (`1..=FORMAT_VERSION`); corrupt/truncated input yields NULL (caller falls back to rescan/reindex), never a partial index. Counts exposed to cheap tooling MUST come from headers — never instantiate the engine to report status (#553 OOM incident).
**Probe:** `src/test_index.zig` :3072 bm25-persistence round-trip; `grep -n "readStatusMeta" src/*.zig` shows the status CLI consumer; `grep -n "FORMAT_VERSION" src/index.zig`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", query: "readDiskHeader writeToDisk postings", limit: 10 });
```

## Verdict
Adopt the dual-consumable serialization (one payload serving heap rebuild, mmap, and header-only readers); adapt field widths to your scale; omit git-head embedding if you track freshness elsewhere — but keep the rule that status surfaces never trigger builds.
