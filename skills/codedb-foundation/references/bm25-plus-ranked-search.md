<!-- capsule-v2 -->
# BM25+ ranked search with lazy top-k heap — what exact scoring variant, and why does N fall back to id_to_path length?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** Which BM25 formula does the multi-word ranker use, and how does it stay correct on bulk-loaded indexes lacking doc lengths?

## BM25 (k1=1.2, b=0.75) + BM25+ delta 0.5, one SearchResult per top doc
**Path/Symbol:** `src/explore.zig:Explorer.searchContentRankedUncached` :5805–6159 (router `searchContentAuto` :6168: space-containing query → ranked, single token → literal).
**Signature:** idf = `log(1 + (N − df + 0.5)/(df + 0.5))` (+1 smoothing); tf_sat = `tf·(k1+1)/(tf + k1·norm)` where `norm = 1 − b + b·dl/avgdl`; term_score = `idf·(tf_sat + 0.5)`.
**Data Shape:** Query tokenized EXACTLY like documents (lowercase + splitIdentifier sub-tokens), deduped into an arena set. Per-term pass builds `doc_best_line: doc → {line, count}`; df = distinct docs; tf = entries-per-doc. Final candidates multiply by `pathRelevanceMultiplier × centralityBoost × graphDistanceBoost × coChangeBoost`, plus NL→symbol bridge `×(1 + 0.6·overlap)`.

### Decisive source
```zig
// Fall back to the total indexed-doc count when the per-doc length table is
// empty (the bulk `codedb index` path writes the disk word index without doc
// lengths) so ranked search still returns idf-weighted results instead of nothing.
const ranked_n = self.word_index.rankedDocCount();
const N: u32 = if (ranked_n > 0) ranked_n else @intCast(self.word_index.id_to_path.items.len);
...
// Lazy top-k via a max-heap: pop candidates in (score desc, doc_id asc)
// order and materialize until max_results survive ... O(C + (k+skips)·log C).
```
Best-line resolution uses the line-offset cache with scan fallback:
```zig
if (self.line_offsets.lineSpans(path, ref.data, lines1[0..], span1[0..])) |n| {
    if (n == 1) break :blk ref.data[span1[0].start..span1[0].end]; ...
}
break :blk extractLineByNumber(ref.data, c.best_line);
```
NL→symbol bridge (≥2 terms): count per-symbol overlap between query terms and splitIdentifier(symbol_name); overlap ≥ 2 ⇒ boost defining file AND repoint its best line at the definition.

**Flow:** lazy-rebuild word index pre-lock (#546 cold-CLI fix) → ensure symbol/def-token indexes for identifier-shaped or multi-word queries → tokenize/dedupe → optional graph-distance build gated on any raw token hitting symbol_index → score all docs → seed co-change only from candidate files that define a query-named symbol → heap-pop top-k, resolving each hit line lazily (freed-doc-id paths skipped).
**Invariant:** df counts DISTINCT docs while tf counts line entries (postings are distinct lines by construction); avgdl returns 1.0 when untracked (safe divide); the heap comparator ties on doc_id asc for deterministic output; every popped candidate re-reads content through readContentForSearch — evicted files simply skip (soundness preserved, recall bounded by cache policy).
**Probe:** `src/test_search.zig` bm25-recall-a…e (:724/:757/:795/:830/:856 — tf ordering, both-terms-beats-high-tf-single, df saturation, length normalization, pathological queries) + bm25-stress 1000-doc cap test.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "searchContentRankedUncached", limit: 10 });
```

## Verdict
Adopt BM25+ (the delta rescues long source files — plain BM25 starves them) and the lazy top-k materialization; adapt k1/b/delta via config as codedb does via constants; omit the NL→symbol bridge unless you also port outline symbol splitting.
