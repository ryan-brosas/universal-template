<!-- capsule-v2 -->
# Phrase docids — windowed pair-proximity intersection

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How are phrase ("quoted") candidates resolved from word-pair proximity postings, and what false-positive handling must survive a port?

## compute_phrase_docids with winsize-3 windows
**Path/Symbol:** `crates/milli/src/search/new/resolve_query_graph.rs:compute_phrase_docids` (:187-268), phrase cache `get_phrase_docids` (:22-31), graph resolution `compute_query_graph_docids` (:133-185), per-fid/position twins (:61-130).
**Signature:** `pub fn compute_phrase_docids(ctx: &mut SearchContext<'_>, phrase: Interned<Phrase>) -> Result<RoaringBitmap>`
**Data Shape:** `Phrase { words: Vec<Option<Interned<String>>> }` — stop words inside a phrase are `None` placeholders that keep positions. Result cached per phrase in `PhraseDocIdsCache`.

### Decisive source
```rust
let winsize = words.len().min(3);
for win in words.windows(winsize) {
    let mut bitmaps = Vec::with_capacity(winsize.pow(2));
    // for every ordered pair (s1 at offset, s2 later in window):
    if dist == 0 { get_db_word_pair_proximity_docids(None, s1, s2, 1)? else return EMPTY }
    else { union dist+1 ..= dist*2? — actually 0..=dist of (dist+1): pairs within gap }
    bitmaps.sort_unstable_by_key(|a| a.len());   // smallest intersections first
    for bitmap in bitmaps { candidates &= bitmap; if candidates.is_empty() { break; } }
}
```

**Flow:** First intersect plain word docids across all non-stop words (any missing word ⇒ ∅ early). Then slide a window of min(len,3) over the phrase; within each window, every ordered pair contributes either an exact-proximity-1 bitmap (adjacent) or the UNION over distances 0..=gap of (gap+1); intersect all pair bitmaps smallest-first.
**Invariant:** (1) Windows cap at 3 because pair postings only encode pairwise proximity — a 4-word phrase is verified through overlapping triples, which is SOUND but relies on transitivity; (2) stop words stay as None to preserve gaps (a stop word consumes a position slot); (3) false positives ARE possible (pair co-occurrence ≠ exact order across window boundaries), which is exactly why `compute_query_term_subset_docids_within_field_id` intersects phrase docids with first-word-in-fid docids instead of trusting them; (4) graph-level resolution processes nodes only after all predecessors, freeing predecessor bitmaps as soon as their successors are resolved (memory bound).
**Probe:** `crates/milli/tests/search/phrase_search.rs:test_phrase_search_with_stop_words_given_criteria` (:27+) pins stop-word position preservation under multiple ranking-rule orders; GREEN via search suites at HEAD.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "compute_phrase_docids", limit: 5 });
```

## Verdict
Adopt windowed-pair phrase resolution + smallest-first intersection ordering; adapt to host's pair-posting encoding; omit codec details. Caveat: pinned by integration tests, not a dedicated unit test.
