<!-- capsule-v2 -->
# Trigram bloom posting masks (next_mask + loc_mask) — which candidate filters are sound, and why must masks be per-FILE not global?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How do two 8-bit Bloom filters per (trigram,file) posting prune candidates before content scan — and what breaks if a porter computes them per-corpus?

## Per-file masks on sorted doc-id postings
**Path/Symbol:** `src/index.zig` (`PostingMask` :1036–1039, `DocPosting` :1041–1045, extraction in `TrigramIndex.indexFile` :1264–1300, refinement in `candidates` :1589–1627).
**Signature:** `loc_mask |= @as(u8, 1) << @intCast(i & 7)` at every occurrence position i; `next_mask |= 1 << (normalizeChar(next_char) & 7)`.
**Data Shape:** One `PostingMask{next_mask, loc_mask}` per (trigram → file) pair, stored in a doc-id-SORTED `PostingList.items`. `loc_mask` bit k = the trigram occurs at some position ≡ k (mod 8); `next_mask` bit k = some occurrence of this trigram is immediately followed by a char whose low-3-bits are k. Whitespace-only trigrams are skipped (~12% of occurrences).

### Decisive source
```zig
const rotated = (mask_a.loc_mask << 1) | (mask_a.loc_mask >> 7);
if ((rotated & mask_b.loc_mask) == 0) continue :next_cand;
if ((mask_a.next_mask & pair.next_bit) == 0) continue :next_cand;
```
with pairs pre-hoisted out of the candidate loop (they depend only on the query):
```zig
const Pair = struct { list_a: ?*PostingList, list_b: ?*PostingList, next_bit: u8 };
// list_a/list_b = consecutive query trigrams j, j+1; next_bit from query[j+3]
```

**Flow:** index-time accumulate masks in a LOCAL per-file map (phase 1), then bulk-insert one posting per trigram (phase 2, append for new docs / sorted insert for reused ids) → query-time: intersect all query-trigram posting lists smallest-first via sorted merge → for each surviving candidate verify EVERY consecutive trigram pair: rotate mask_a's loc_mask left by 1 (adjacent positions shift phase by 1 mod 8) and require overlap with mask_b's loc_mask; require mask_a's next_mask to contain the following char's bit.
**Invariant:** Masks are PER-FILE aggregates of ALL positions — a global table would reject valid files that contain the trigram pair in different positional phases. The filters are sound (may only drop candidates when the pattern truly cannot match; "bloom: soundness — never rejects actual matches") and best-effort (a pass still requires exact content verification downstream). Sorted-posting invariant is what makes `getByDocId` binary search and mmap merge work.
**Probe:** `src/test_index.zig` :1524–1719 — "bloom: PostingMask is populated during indexing", "bloom: loc_mask records correct position bits", "bloom: soundness — never rejects actual matches", "bloom: reduces candidates vs pure trigram intersection", "bloom: loc_mask adjacency filtering works".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", query: "PostingMask candidates bloom", limit: 10 });
```

## Verdict
Adopt the two-mask scheme and the rotation-overlap check (it kills ~all false candidates with zero false negatives); adapt bit width to your alphabet; omit nothing here — but note MAX_POSTINGS=256 caps common-trigram lists (poor discriminators), which a porter must replicate or consciously raise.
