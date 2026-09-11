<!-- capsule-v2 -->
# LineOffsetCache self-validating span tables — how do you cache byte offsets derived from cacheable content without stale-pointer bugs?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** What identity check makes a cached derived structure safe when its source bytes can be evicted and reallocated?

## ptr+len identity + 16 MiB budget + clear-on-overflow
**Path/Symbol:** `src/explore.zig:LineOffsetCache` :964–1125 (`offsetsForLocked` :1041, `lineSpans` :1074, `appendRange` :1095).
**Signature:** entry = `{content_ptr: usize, content_len: usize, offsets: []u32}`; hit requires BOTH `content_ptr == @intFromPtr(content.ptr)` AND `content_len == content.len`; `MAX_BYTES = 16 MiB` enforced lazily after each serve (`if (total_bytes > MAX_BYTES) clearLocked()`).
**Data Shape:** offsets[i] = byte offset of line i+1 (built by scanning '\n'); span end = `offsets[ln] - 1` (drop '\n') or content.len for the final line — semantics EXACTLY matching `std.mem.splitScalar(content,'\n')`. Own mutex because it mutates under the Explorer's SHARED lock (concurrent readers may build entries).

### Decisive source
```zig
if (self.map.getPtr(path)) |entry| {
    if (entry.content_ptr == @intFromPtr(content.ptr) and entry.content_len == content.len) {
        return entry.offsets;
    }
    const fresh = buildOffsets(...) orelse return null;
    ... replace ...
}
```
Consumers pair it with ContentHashCache (same pattern keyed on generation) and use it to replace scan-from-zero line extraction:
```zig
// Resolve the hit line via the line-offset cache (O(log n)) with the
// scan-from-zero extractLineByNumber as fallback — the same swap the
// exact-recall tiers made in #611 ... On real repos this was up to
// max_results whole-file walks per ranked query.
```

**Flow:** Tier 0/BM25 resolve target lines → lineSpans consults/builds the table under mu → fills caller-provided `[256]Span` arrays (no per-query allocation) → overflow clears the WHOLE cache (simplest correct policy under a budget). Null return (OOM) routes callers to the scanning fallback — never an error surfaced.
**Invariant:** A cached offsets table is valid ONLY while the exact backing buffer lives — ptr+len equality is the cheap proxy; mutation paths invalidate explicitly too ("so allocator reuse cannot serve a stale result"). Ascending target_lines required (spans fill in order). Derived caches must degrade to recompute, never fail the query.
**Probe:** `src/test_explore.zig` "cached deep reads and fuzzy finds invalidate exactly"; `src/test_search.zig` tier0 line-hits audit (:1936) exercises the span path; mechanical: `grep -n "content_ptr" src/explore.zig`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "LineOffsetCache", limit: 10 });
```

## Verdict
Adopt pointer-identity validation for any memoized derivation over pooled/reusable buffers; adapt the budget to your workload; omit the fixed [256] stack-span micro-optimization if your language heap-allocates cheaply.
