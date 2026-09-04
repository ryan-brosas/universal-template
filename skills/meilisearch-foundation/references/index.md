<!-- Preserved from the pre-foundation-skill-v1 loader. Detail remains historical and revision-pinned. -->


# Meilisearch (milli): typo-tolerant search engine foundation

## Use this for
Use when implementing or fixing typo tolerance, prefix/ngram/synonym term expansion, ranking-rule pipelines, cheapest-path bucketing, phrase candidate resolution, exact-attribute semantics, OR when building the facet level-tree (bulk rebuild / incremental update), range filtering, facet sorting, facet-value search, facet distribution, the filter expression grammar, or filter evaluation over facet databases in a search engine. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `./typo-budget-ladder.md` — how many typos a word gets (settings ladder, chars-not-bytes, exact-words veto).
- `./derivation-lazy-engine.md` — lazy 0/1/2-typo + split-word expansion against the FST; first-letter-counts-double.
- `./query-graph-construction.md` — the DAG of query interpretations: ngram fan-out, wrapping positions, word-dropping ladders.
- `./ranking-rule-graph-trait.md` — the 3-method trait that turns any cost model into a per-rule condition DAG.
- `./cheapest-path-visitor.md` — DFS path enumeration pruned by precomputed cost tables + prefix-scoped dead-ends trie.
- `./bucket-sort-executor.md` — recursive ranking-rule executor: shrinking queries, score stacks, honest estimates, degraded deadline mode.
- `./db-cache-pointer-intersection.md` — pointer-cached postings with universe-intersecting decode; ByAttribute proximity collapse.
- `./phrase-docids-windowing.md` — windowed pair-proximity intersection for quoted phrases; stop words keep positions.
- `./interner-memory-discipline.md` — u16 handles, dedup→fixed-size freeze, bitset sets; the memory architecture under everything.
- `./ranking-rules-assembly.md` — settings criteria → concrete pipeline, legacy Attribute expansion, Words-first coercion.
- `./token-fsm-phrases-negatives.md` — tokenizer FSM: quote buffering, `-` negatives, last-token prefix rule.
- `./exact-attribute-gate.md` — exact vs tolerant field partition; exact_word_docids twin DBs union into candidates, ranking-separated exactness.

### Facet levels & filtering plane (pass 2)
- `./facet-level-navigation.md` — the 3-byte key-prefix tricks that read tree height and first/last value in O(1).
- `./facet-bulk-rebuild.md` — bottom-up level rebuild: group-OR fold, min_level_size flush gate, leftover propagation (#3165).
- `./facet-bulk-incremental-dispatch.md` — delta-size/500-keys ratio picks rebuild vs modify; disabled-facet-search clear path.
- `./facet-incremental-modify.md` — six-state ModificationResult FSM: split at max_group_size, trim-before-delete, deferred level grow/shrink.
- `./facet-new-incremental-reverse-sweep.md` — reverse-lexicographic parent recompute with last-parent cache and adaptive group sizing.
- `./facet-range-descent.md` — skip/stop/take-whole-group/recurse ladder over implicit `[own, next)` ranges.
- `./facet-sort-iterators.md` — lazy stack-machine sorts with subtract-on-emit; descending twin's right-bound narrowing.
- `./facet-value-search.md` — facet-search autocomplete: normalized FST + typo DFA(prefix), original-string backfill, dual collection orders.
- `./facet-distribution-switch.md` — 3000-candidate threshold between per-doc counting and level-tree iteration; count-heap ordering.
- `./filter-grammar-precedence.md` — descent-chain precedence (or→and→not→primary), cut-after-keyword, parse-time NOT cancellation.
- `./filter-value-lexer.md` — bare-word character class, keywords legal quoted, two-layer escape story, geo misuse guards.
- `./filter-condition-operators.md` — IS NULL/CONTAINS/STARTS WITH as Not-wrapped positives; `_vectors.` commit-after-dot paths.
- `./filter-evaluation-tree.md` — universe-threading AND fold; equality/starts-with/contains fast paths over the facet DBs.
- `./filter-constraint-extraction.md` — DNF constraint sets under polarity flips with saturating or/and/depth fuel.

## Capsule map
- **Typo tolerance** — `typo-budget-ladder`: 0/1/2-typo budget closure over authorize_typos + length thresholds (chars) + exact_words FST.
- **Typo tolerance** — `derivation-lazy-engine`: Lazy::Uninit→Init derivation lattice computed on demand; dfa(1) complemented with StartsWith(first char) so first-letter typos are always distance 2; split-best-frequency heuristic.
- **Query understanding** — `query-graph-construction`: START/END/Term/Deleted nodes; consecutive-position ngrams (≤3) as alternative readings; minimal-next-tier edges; removal orders never drop the last interpretation.
- **Query understanding** — `token-fsm-phrases-negatives`: hard-separator position jump (+7), phrase builder with None stop-word slots, negative latch, trailing-token prefix search.
- **Ranking rules** — `ranking-rule-graph-trait`: build_edges/resolve_condition/rank_to_score contract; ngram base costs; skip edges priced by matching strategy.
- **Ranking rules** — `ranking-rules-assembly`: settings→pipeline compiler; at-most-once instantiation; Exactness = ExactAttribute+Exactness pair; placeholder/vector variants strip query-dependent rules.
- **Execution** — `bucket-sort-executor`: nested bucket loops with back!(); child universe+query from parent bucket; distinct/threshold/offset estimate bookkeeping; pins injection; degraded=true on deadline.
- **Execution** — `cheapest-path-visitor`: all-costs-to-end table + DeadEndsCache trie kill exponential DFS; post-mutation forbidden-prefix recheck; incremental cost-table repair.
- **Execution** — `db-cache-pointer-intersection`: Cow byte-pointer cache keyed by interned words; CboRoaringBitmapCodec::intersection_with_serialized applies universes without full decode.
- **Execution** — `interner-memory-discipline`: Interned<u16> handles, DedupInterner.freeze() to FixedSizeInterner, SmallBitmap sets; <65,536 values per interner.
- **Phrase & attributes** — `phrase-docids-windowing`: min(len,3)-windows of ordered pairs, smallest-bitmap-first intersections, false-positive caveat for cross-window order.
- **Phrase & attributes** — `exact-attribute-gate`: exact_attributes partition fids once in SearchContext; exact_word_docids twin DBs union into candidates; disableOnNumbers zeroes budgets for numeric words.
- **Facet levels & filtering (pass 2)** — `facet-level-navigation`: `[fid BE][level][bound]` key arithmetic — rev-prefix scan for height, level-0 prefix for extremes. `facet-bulk-rebuild`: recursive group-OR fold; write a level only at min_level_size entries, else propagate leftovers UP (#3165). `facet-bulk-incremental-dispatch`: `data_size >= db.len()/501` ⇒ bulk rebuild else incremental; disabled facet-search clears its two DBs. `facet-incremental-modify`: InPlace/Expand/Insert/Reduce/Remove/Nothing FSM; split at max_group_size; trim_del_docids before subtracting; add_or_delete_level deferred per field. `facet-new-incremental-reverse-sweep`: reverse-sorted changes + last-parent cache recompute parent groups with adaptive group_size. `facet-range-descent`: skip/stop/take-whole-group/recurse judged on NEXT-key implicit ranges. `facet-sort-iterators`: stack-machine lazy sorts, subtract-on-emit exactly-once; descending needs per-frame right_bound. `facet-value-search`: normalized-FST DFA(0/1/2, prefix) ladder → originals DB backfill; Lexicographic breaks at max, Count heap-evicts. `facet-distribution-switch`: ≤3000 candidates + lexicographic ⇒ per-doc count else level iterators; count heap orders by (count desc, Reverse(level)). `filter-grammar-precedence`: or→and→not→primary descent = precedence; cut after keywords; depth 150 counts NESTING not terms. `filter-value-lexer`: word = alnum|_|-|.; keywords rejected bare but legal quoted; quote-unescape then full unescape layers. `filter-condition-operators`: IS NOT NULL/NOT CONTAINS wrap positives in Not; `_vectors.` commits to failure paths. `filter-evaluation-tree`: AND passes running bitmap as child universe; equal = twin point lookups; starts-with = last-byte-increment range. `filter-constraint-extraction`: polarity walk turns OR/AND into branch-maps vs cartesian fuses under saturating fuel.

## Extending the foundation
Add one `./<seam>.md` capsule for one graph-selected, source-confirmed porting question (candidates: facet/filters plane, index-time extract/* pipelines, vector_sort/geo_sort). Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
meilisearch (MIT), `main@577f7af28942b71782eab1e59f44ad8296ce0a92`; Codebase Memory project `ext-meilisearch` (18,405n/98,687e, FULL mode, generation 2026-08-23T11:50:29Z, head==base==pin, zero parse_partial on cited files; 12 asset files excluded by design). Pass 2 (2026-08-24) added the facet levels & filtering plane at the SAME pin — zero upstream drift, graph re-verified live (`index_status` ready, 15/15 new seams rank-1 line-exact); real runner `cargo test -p filter-parser --lib` = 11 passed + `cargo test -p milli --lib -- facet` GREEN at pin (warm cache `/tmp/meili-probe`, TMPDIR redirected to $HOME after shared-/tmp quota hits).

## Full view (memory graph)
Revalidate `ext-meilisearch` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root (`$REFERENCE_ROOT/external/meilisearch`), branch main, commit `577f7af2`, FULL mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. Note: this CLI's `--name-pattern` takes plain substrings (regex `(?i)` flags silently return zero hits); `search_graph --semantic-query` must be an array.

## Boundaries
Adopt pure contracts: typo budget ladder, derivation lattice + subset algebra, query-graph construction, cheapest-path pruning structures, bucket executor invariants, interner discipline; facet level-tree key layout and its bulk/incremental update algorithms; the filter grammar (precedence, escaping, negation shapes) and its evaluation over posting bitmaps. Adapt host-specific integration: LMDB/heed database layout, charabia tokenization, roaring/CBO bitmap codecs, score_details serialization. Omit source-specific transport/product behavior: HTTP routes, index-scheduler task queue, dump versioning, API-key auth, dashboards, cellulite geojson storage internals.

## Reference-file inventory

Every preserved capsule/reference file in this foundation:

- [`bucket-sort-executor.md`](./bucket-sort-executor.md)
- [`cheapest-path-visitor.md`](./cheapest-path-visitor.md)
- [`db-cache-pointer-intersection.md`](./db-cache-pointer-intersection.md)
- [`derivation-lazy-engine.md`](./derivation-lazy-engine.md)
- [`exact-attribute-gate.md`](./exact-attribute-gate.md)
- [`facet-bulk-incremental-dispatch.md`](./facet-bulk-incremental-dispatch.md)
- [`facet-bulk-rebuild.md`](./facet-bulk-rebuild.md)
- [`facet-distribution-switch.md`](./facet-distribution-switch.md)
- [`facet-incremental-modify.md`](./facet-incremental-modify.md)
- [`facet-level-navigation.md`](./facet-level-navigation.md)
- [`facet-new-incremental-reverse-sweep.md`](./facet-new-incremental-reverse-sweep.md)
- [`facet-range-descent.md`](./facet-range-descent.md)
- [`facet-sort-iterators.md`](./facet-sort-iterators.md)
- [`facet-value-search.md`](./facet-value-search.md)
- [`filter-condition-operators.md`](./filter-condition-operators.md)
- [`filter-constraint-extraction.md`](./filter-constraint-extraction.md)
- [`filter-evaluation-tree.md`](./filter-evaluation-tree.md)
- [`filter-grammar-precedence.md`](./filter-grammar-precedence.md)
- [`filter-value-lexer.md`](./filter-value-lexer.md)
- [`interner-memory-discipline.md`](./interner-memory-discipline.md)
- [`phrase-docids-windowing.md`](./phrase-docids-windowing.md)
- [`query-graph-construction.md`](./query-graph-construction.md)
- [`ranking-rule-graph-trait.md`](./ranking-rule-graph-trait.md)
- [`ranking-rules-assembly.md`](./ranking-rules-assembly.md)
- [`token-fsm-phrases-negatives.md`](./token-fsm-phrases-negatives.md)
- [`typo-budget-ladder.md`](./typo-budget-ladder.md)
