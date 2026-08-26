---
name: codedb-foundation
description: "Code-intelligence search engine foundation"
---
# codedb: Code-Intelligence Search Engine Foundation

## Use this for
Use when building or porting local code-search/retrieval engines: typo-substring trigram indexes with bloom pruning, inverted word indexes with BM25+ ranking, content-defined n-gram indexes, mmap zero-copy persistence, deterministic call/import graphs, generation-safe result caches, and tiered recall ladders for agent context tools. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/word-index-mmap-promotion.md` — When does a read-only index pay heap materialization, and what state does each mode hold?
- `references/word-index-removal-and-shards.md` — How do bulk-loaded docs get deleted, and why does merged shard order reproduce serial doc ids?
- `references/trigram-bloom-masks.md` — Which candidate Bloom filters are sound, and why must masks be per-file?
- `references/regex-decomposition-soundness.md` — When must regex prefiltering be abandoned entirely to avoid silent misses?
- `references/sparse-ngram-boundaries.md` — How do variable content-defined n-grams stay substring-searchable without alignment?
- `references/trigram-overlay-lattice.md` — Why promote an mmap index to base+overlay instead of materializing on first write?
- `references/disk-format-status-meta.md` — What does OOM-proof lazy loading look like, and which counts must never build the engine?
- `references/tiered-search-ladder.md` — Where does each tier early-exit and which tiers are provably skippable?
- `references/rerank-signal-composition.md` — Which boosts are multiplicative ≥1 (never filters) and how do priors layer?
- `references/bm25-plus-ranked-search.md` — What exact BM25 variant runs, and why does N fall back when doc lengths are missing?
- `references/bm25-accounting-subtokens.md` — Which fields constitute ranking state, and when is an identifier split?
- `references/call-graph-weight-split.md` — How are calls resolved without type info, and why must graph signals be additive-only?
- `references/import-graph-basename-duality.md` — When must basename matching in imported-by be refused as ambiguous?
- `references/content-cache-clock-borrowed.md` — How does one cache hold owned copies and borrowed mmap views under a byte budget?
- `references/generation-caches.md` — What makes caching search results safe while lazy signals build mid-flight?
- `references/line-offset-cache.md` — What identity check keeps cached byte-offset tables stale-proof over reusable buffers?
- `references/lazy-completion-latches.md` — Which completion flags gate "index complete" and how do fast-loaded snapshots defer honestly?

## Capsule map
- **Zero-copy word index** — `word-index-mmap-promotion`: mmap view + promote-on-first-write; reads never mutate, exactly one materialization per load.
- **Removal dual-path & shard parity** — `word-index-removal-and-shards`: tracked fast path vs bulk sweep; offset-by-base merges reproduce serial id assignment transactionally.
- **Bloom posting masks** — `trigram-bloom-masks`: per-(trigram,file) next_mask+loc_mask; rotate-and-overlap adjacency check prunes candidates soundly.
- **Regex prefilter compiler** — `regex-decomposition-soundness`: literal-run AND trigrams / alternation OR groups; any trigram-empty branch ⇒ scan everything (#628).
- **Sparse n-grams** — `sparse-ngram-boundaries`: boundaries at pairWeight strict local maxima, 16-char cap, full sliding-window covering set on queries.
- **Overlay lattice** — `trigram-overlay-lattice`: heap/mmap/mmap_overlay union; immutable base + mask set + heap overlay; persist re-materializes via tmp+rename over the live mapping.
- **Two-file disk format** — `disk-format-status-meta`: contiguous postings + offset lookup table consumable by heap reload, direct mmap, and 51-byte header status readers.
- **Tier ladder** — `tiered-search-ladder`: Tier 0 word → prefix → trigram candidates → skip-trigram → outline scan, shared dedup set, proof-based skips, always rerank.
- **Rerank composition** — `rerank-signal-composition`: definition-line +5, eponymy +15/+8/+6, path-class demotions only, graph boosts always ≥1, packed-key sort.
- **BM25+ ranker** — `bm25-plus-ranked-search`: k1=1.2 b=0.75 delta=0.5, N falls back to doc count, lazy top-k max-heap, NL→symbol bridge.
- **Ranking-state accounting** — `bm25-accounting-subtokens`: doc_lengths/total_tokens triple; sub-token gate = len≥4 ∧ has `_`|uppercase; dual whole+split indexing.
- **Call graph** — `call-graph-weight-split`: comment/string-aware callee extraction, weight split across ambiguous definitions, PageRank default, radj prebuilt once.
- **Import graph** — `import-graph-basename-duality`: forward list + reverse set + arena interning; basename fallback gated by ambiguity; bounded BFS variants.
- **Content cache** — `content-cache-clock-borrowed`: 8-way CLOCK, owned/borrowed duality, oversize puts drop stale entries, budget sweep skips borrowed.
- **Result caches** — `generation-caches`: gen sampled before search + env fingerprint keying; hits can never observe state fresh searches wouldn't produce.
- **Line offsets** — `line-offset-cache`: ptr+len identity validation, 16 MiB clear-on-overflow, span semantics identical to newline splitting.
- **Completion latches** — `lazy-completion-latches`: deferred planes rebuild at use sites pre-lock; never consume or cache from incomplete state (#539/#546/#564).

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
codedb (MIT), `main@43bc3ca2` (v0.2.5843); Codebase Memory project `ext-codedb` (10,339n / 35,286e, ready; parse_partial limited to bench `.patch` fixtures — no cited file affected).

## Full view (memory graph)
Revalidate `ext-codedb` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Graph root `/mnt/hdd/utopia/inspo/external/codedb`, branch main @ `43bc3ca265a581de13aa7bb7bc18ce13cfa3f514` (head==base at pass-1 pin). Direct-test suites live beside sources (`src/test_index.zig`, `src/test_search.zig`, `src/test_explore.zig`, `src/adversarial_tests.zig`) and run via `zig build test`; source and direct tests decide shipped claims.

## Boundaries
Adopt the index/rerank/cache contracts (trigram+bloom, BM25+, overlay persistence, additive-only graph signals, generation-keyed caching). Adapt language-specific outline parsers and import resolvers (per-language shims are host surface) and allocator/locking strategy to your runtime. Omit codedb's product transport — MCP server framing (`mcp.zig`), HTTP server (`server.zig`), CLI daemon/proxy plumbing, auto-update and telemetry — none of it affects retrieval correctness.
