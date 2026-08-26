<!-- capsule-v2 -->
# Tiered search ladder (Tier 0 word → prefix → trigram → skip-trigram → outline scan) — where does early exit happen and what does each tier cost?

**Source:** codedb MIT `main@43bc3ca2`; Codebase Memory `ext-codedb`. **Question:** How does one search entry point combine inverted-index precision with guaranteed recall, stopping at the cheapest sufficient tier?

## Early-exit tier cascade with shared `searched` dedup set
**Path/Symbol:** `src/explore.zig:Explorer.searchContentUncached` :4209–4648 (front-door cache wrapper `searchContent` :4190–4207).
**Data Shape:** `SearchBreakdown{tier_reached, candidate_count, result_count, tier0_ns...rerank_ns, cache_hit}` recorded per query for telemetry/provenance; `searched: StringHashMap(void)` prevents any path being scanned twice across tiers.
**Pre-lock lazy rebuilds:** before taking the shared lock, Tier 0 forces `rebuildWordIndex` when `word_index_complete == false` (#539 — without it recall collapses to trigram tiers and restored files get crowded out), and identifier-shaped queries force `ensureSymbolIndex` (#564) for the rerank graph gate.

### Decisive source
```zig
// Tier 0: word index direct lookup — O(1) hash lookup plus bounded content
// extraction. A per-file cap forces diversity ... Files that DEFINE a symbol
// named by the query are considered first (#546 ...), then code before docs,
// then files with more exact word hits ...
const tier0_per_file_cap: usize = if (tier0_files.items.len <= 1) max_results else @max(1, max_results / 5);
const use_line_hits = tier0_exact_capacity >= max_results and tier0_per_file_cap <= 256;
if (result_list.items.len >= max_results) { ...rerankAndFinalize...; return res; }
```
Tier ordering after 0 (each returns early when quota filled):
- **0.5** `word_index.searchPrefix(query)` — strictly-longer keys only, verified by case-insensitive containment in the line.
- **1** `trigram_index.candidates(query)` — candidate paths ranked by per-file word-hit count desc then content length asc (#427: definition-dense files scan first), `max_per_file = max(1, max_results/estimated_total)`.
- **3** `skip_trigram_files` scan (files indexed without trigrams, e.g. >size or canonical docs).
- **4** re-scan all word-hit paths not yet searched.
- **5** FULL outline-map scan — ONLY when `result_list.items.len == 0 and !trigram_ruled_out`; a non-empty candidate list for a ≥3-char query PROVES the trigram filter ran, so tier 5 is skipped (it cannot find what trigrams ruled out).
(Tier 2, the sparse-ngram fallback, was REMOVED in v0.2.5822 — fields remain for breakdown compatibility.)

**Flow:** ensure-lazy-state → lockShared → Tier 0 groups posting runs per file (contiguous-run detection avoids building a dedup table at all; falls back to slot array/hash map when swap-removal fragmented order) → sort by packed u64 key `(is_doc | !defines | ~count | index)` → emit line hits via LineOffsetCache spans (fast path gated on capacity math) → early-return to rerank at whichever tier fills the quota → final `rerankAndFinalize` always runs.
**Invariant:** Every tier marks `searched` BEFORE scanning it; quota check happens between files, not lines; the trigram_ruled_out gate makes tier 5 unreachable rather than redundant work. `use_line_hits` early-return intentionally SKIPS per-line basename boosts — pinned by its own audit test.
**Probe:** `src/test_search.zig` :1936 "audit: searchContent tier0 use_line_hits early-return skips rerank basename boost"; :2025 "audit: searchContent loses a word-indexed file >512KB evicted from the content cache"; `src/test_explore.zig` Explorer integration tests.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codedb", name_pattern: "searchContentUncached", limit: 10 });
```

## Verdict
Adopt the cheapest-sufficient-tier discipline with cross-tier dedup and proof-based skips; adapt tier composition to your index inventory; omit the packed-u64 sort micro-optimizations unless porting to a systems language.
