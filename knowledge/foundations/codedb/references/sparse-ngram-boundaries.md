<!-- capsule-v2 -->
# Content-defined sparse n-grams (pairWeight local maxima + covering-set queries) — how do variable n-grams stay substring-searchable without alignment?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How do you index variable-length n-grams chosen by CONTENT so arbitrary query substrings still hit, given boundaries fall differently in files vs queries?

## Boundary-at-local-maxima extraction, sliding-window query side
**Path/Symbol:** `src/index.zig` (`MAX_NGRAM_LEN=16` :3156, `default_pair_freq` comptime table :3162–3228, `pairWeight` :3240–3245, `extractSparseNgrams` :3468–3533, `buildCoveringSet` :3540–3559, `SparseNgramIndex.candidates` union :3640–3676).
**Signature:** `pub fn pairWeight(a: u8, b: u8) u16` = `freq_weight +| jitter(0..255)` where jitter = `@truncate(Wyhash.hash(0,&[a,b]) & 0xFF)`; `extractSparseNgrams(content) ![]SparseNgram{hash,pos,len}`.
**Data Shape:** Index side stores Wyhash(lowercased ngram) → set of paths (+ per-file contributed hash lists for cleanup). Query side materializes EVERY query substring of length [3,16] as a hash. MIN_LEN=3 mirrors trigram floor.

### Decisive source
```zig
// Collect boundary pair-positions: always include 0 and pair_count-1,
// plus any interior strict local maximum.
for (1..pair_count - 1) |i| {
    if (weights[i] > weights[i - 1] and weights[i] > weights[i + 1]) bounds.append(i);
}
...
} else {
    // Force-split into MAX_NGRAM_LEN-sized chunks ... Tail too short:
    // Overlap with the previous chunk by backing up to ngram_end - MIN_LEN
    // so every byte in the span is covered.
    try result.append(makeNgram(content, ngram_end - MIN_LEN, MIN_LEN));
}
```
Query-side answer to misalignment:
```zig
/// Extracts every substring of the query with length in [3, MAX_NGRAM_LEN] so
/// that file boundary-based n-grams overlapping the query are matched regardless
/// of where content-defined boundaries fall in the indexed file.
```

**Flow:** weight every adjacent normalized byte pair (common source bigrams like `th`,`fn`,`::` get LOW weight 0x1000; unspecified default 0xFE00 rare/high) → boundaries at strict local maxima + endpoints → emit n-grams spanning consecutive boundaries, force-splitting >16 spans into 16-chunks with a ≥3-byte overlapping tail piece → hash each into the inverted map. Queries take the UNION of all sliding-window hash posting sets — a superset verified later by real content scan.
**Invariant:** Frequency tables are swappable ONLY between indexing runs (`setFrequencyTable` copies into a static; "swap only before indexing starts"); the covering set makes the index side's choice of boundaries irrelevant to recall — dropping it is the classic porting bug (query hashes miss file-boundary hashes entirely). Union-not-intersect on the query side preserves soundness.
**Probe:** `src/adversarial_tests.zig` :182–300 ("extractSparseNgrams on exactly 3-byte content", "...MAX_NGRAM_LEN boundary", "...all-same-character content", "...binary-like content with null bytes"; "buildCoveringSet hashes match extractSparseNgrams for 3-byte content"), "adversarial: pairWeight common pairs have lower weight than rare pairs" + determinism/null-bytes tests; `src/test_index.zig` buildCoveringSet short-query/covering-window tests.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "extractSparseNgrams", limit: 10 });
```

## Verdict
Adopt content-defined chunking + full covering-set queries as the general recipe for hash-based substring indexes beyond fixed k; adapt the frequency table (or learn it per-project via `buildFrequencyTableFromMapParallel`); omit the persisted `pair_freq.bin` plumbing if you recompute per session.
