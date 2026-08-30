<!-- capsule-v2 -->
# WordIndex BM25 accounting + identifier sub-token indexing — which fields constitute the ranking state, and when does an identifier get split?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** What must stay in sync for BM25 to work, and what is the exact sub-token gate?

## doc_lengths / total_tokens as THE ranker's source of truth
**Path/Symbol:** `src/index.zig` (`rankedDocCount` :636, `docLength` :641, `avgDocLength` :647–652, indexFile token loop :298–353, v3 disk trailer :768–786).
**Signature:** `avgDocLength()` returns 1.0 when untracked (safe divide); `indexFile` records `doc_lengths[doc_id] = doc_token_count` and maintains `total_tokens` with wrapping arithmetic symmetric on remove.
**Data Shape:** Token = `WordTokenizer` run of `[A-Za-z0-9_]`, len ≥ 2 (shorter skipped BEFORE counting); per-line dedup via last-element check; lowercase via `normalizeChar` into a 256-byte stack buffer (heap fallback only for >256 identifiers).

### Decisive source
```zig
// Sub-tokens from identifier splitting (camelCase, snake_case, etc.).
// Skip the alloc'd ArrayList when the word is too short or all-lower
// (no split possible).
var needs_split: bool = false;
if (word.len >= 4) {
    for (word) |c| { if (c == '_' or (c >= 'A' and c <= 'Z')) { needs_split = true; break; } }
}
if (needs_split) {
    splitIdentifier(word, &sub_toks, aa);
    for (sub_toks.items) |sub| try indexOneToken(self, sub, doc_id, line_num, tracked_words);
}
```
splitIdentifier boundaries (:3115–3153): `_`; lower→Upper; digit↔letter transition; acronym end `HTTPHandler → HTTP|Handler` (Upper followed by Upper then Lower). Both full word AND sub-tokens are indexed — the full camelCase name remains searchable verbatim.

**Flow:** line scan → tokenize → stack-lowercase → indexOneToken (dupe-on-first-insert with rollback; adjacent-dup suppression) → conditional sub-split → compact the words_set into the per-file tracking slice → update doc length counters. The v3 disk trailer persists `(file_id → length)` + total so a reload restores ranking state exactly.
**Invariant:** df/tf math downstream treats each posting as a distinct LINE (per-line dedup at insert); `fileCount()` counts file_words but the RANKER must read `rankedDocCount()` = doc_lengths.count() — bulk-loaded docs have no word sets yet are still ranked. Sub-tokens are emitted only from the SAME arena as the stack-buffer fallback so ownership stays uniform.
**Probe:** `src/test_index.zig` "bm25-persistence" (:3072); `src/test_search.zig` bm25-recall-a…e pin behavioral consequences of the accounting; `grep -n "needs_split" src/index.zig`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "splitIdentifier", limit: 10 });
```

## Verdict
Adopt dual indexing (whole identifier + split parts) with the ≥4-and-has-separator gate; adapt case-folding to Unicode if needed (codedb is ASCII-only by design); omit nothing in the accounting triple (doc_lengths, total_tokens, avgdl fallback) — BM25 silently degrades without it.
