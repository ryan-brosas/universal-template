---
name: duckdb-vectorized-foundation
description: "Use when porting DuckDB's vectorized execution core — vector formats, expression executor, adaptive filters — or building a tuple-filter pipeline that must handle flat, constant, dictionary, sequence, and shredded encodings without materialization. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval."
---
# DuckDB: vectorized execution core (vector formats, expression executor, adaptive filters)

## Use this for
Use when porting DuckDB-style vectorized (columnar batch) execution into another engine or building a tuple-filter pipeline that must handle flat, constant, dictionary, sequence, and shredded encodings without materialization. Source code and direct tests are ground truth; references carry decisive excerpts and graph retrieval.

## Load the matching source dump
- `references/orrify-unified-format.md` — How do you read ANY vector without materializing it? (UnifiedVectorFormat / Orrify protocol, per-type free conversion.)
- `references/selection-vector-identity.md` — How do you filter tuples without copying them? (Three-state SelectionVector, identity sentinel, sel composition.)
- `references/reference-not-copy.md` — When does an operation alias buffers vs. copy? (Reference/Slice/Dictionary triad, deleted copy ctor, Flatten as the only logical-preserving mutation.)
- `references/vector-layout-zoo.md` — Which encodings must an operator tolerate? (BufferType×VectorType matrix, nested child recursion rules.)
- `references/constant-folding-execution.md` — When can a whole chunk be computed once? (all-constant fold protocol, VOLATILE veto, cardinality restore.)
- `references/case-selection-threading.md` — How does CASE run each branch only on tuples that reach it? (WHEN funnel, FillSwitch scatter, short-circuit semantics.)
- `references/conjunction-select-funnel.md` — How does an AND/OR chain evaluate each predicate on the shrinking survivor set? (AND/OR duality, sort-on-OR rule.)
- `references/adaptive-filter-permutation.md` — How do conjunctions learn their cheapest predicate order at runtime? (Swap/observe/revert loop, CanThrow veto.)
- `references/select-vs-execute.md` — Why do predicates have a Select entry point? (Native select paths, outer-space index mapping, NO_NULL template arms.)
- `references/dictionary-reuse-optimization.md` — How is a scalar function evaluated once per dictionary VALUE? (Eligibility gates, same-sel re-emission, id-keyed cache.)
- `references/dictionary-entry-identity.md` — How does dictionary identity survive re-encoding? (id + global_dictionary contract through Reinterpret.)
- `references/data-chunk-reset-caching.md` — How do executors reuse buffers across millions of chunks allocation-free? (Parallel VectorCache slots, type-copy rationale, Reset contract.)
- `references/constant-null-semantics.md` — How are constant NULLs represented and propagated into STRUCT/ARRAY children?
- `references/debug-vector-verification.md` — How does DuckDB stress operators against adversarial encodings in debug builds?

## Capsule map
- **Unified read format (Orrify)** — `orrify-unified-format`: element *i* = `data[sel->get_index(i)]`; flat/constant/dictionary convert for free, exotic layouts flatten first.
- **Tuple indirection** — `selection-vector-identity`: owning/borrowing/unset selection vectors; unset == identity mapping; composition `result[i] = target[new[i]]`.
- **Zero-copy algebra** — `reference-not-copy`: Reference aliases (type-checked), Slice wraps the same buffer with a sel, Dictionary shares a compressed child; copy ctor deleted.
- **Format matrix** — `vector-layout-zoo`: 9 buffer types × 6 vector types; STANDARD..ARRAY serve FLAT+CONSTANT; nested children recurse with independent lengths.
- **Constant folding** — `constant-folding-execution`: all-constant args ⇒ run callback on cardinality 1, restore child cardinality, stamp result CONSTANT; VOLATILE never folds.
- **CASE funnel** — `case-selection-threading`: WHEN Select splits matched/unmatched; THEN executes on matches only; FillSwitch scatters by sel; outer sel re-applied last.
- **Conjunction funnel** — `conjunction-select-funnel`: AND shrinks survivors via true_sel chaining, OR accumulates passes and sorts true_sel before returning.
- **Adaptive filter order** — `adaptive-filter-permutation`: random adjacent swaps every 20 filters, observed over 10, kept iff latency dropped else reverted with likeliness decay; throwing children disable it.
- **Select entry point** — `select-vs-execute`: conjunctions and functions-with-select-callback emit selections natively; DefaultSelect materializes stack bools then gathers, indices always in caller space.
- **Dictionary reuse** — `dictionary-reuse-optimization`: consistent/non-volatile/non-throwing + one non-const input + storage dict ≤20k (+fill-ratio guard) ⇒ compute f(child) once per dict id, re-emit under input sel.
- **Dictionary identity** — `dictionary-entry-identity`: Reinterpret re-mints the entry but id and global flag survive together; caches key on the id string.
- **Chunk reset caching** — `data-chunk-reset-caching`: parallel data/vector_caches slots; types copied at init to dodge atomic refcount contention; Reset rewinds to cached flat buffers.
- **Constant NULLs** — `constant-null-semantics`: null = validity bit 0 cleared on size-1 storage; buffer-class-gated reuse; STRUCT cascades to children, ARRAY nulls row slots.
- **Debug encoding injection** — `debug-vector-verification`: debug_verify_vector wraps every expression result as dictionary / VARIANT-round-trip / shredded to break flat-only assumptions loudly.

## Extending the foundation
Add one `references/<seam>.md` capsule for one graph-selected, source-confirmed porting question. Add one matching loader line and map entry; keep evidence in the capsule, not this leaf.

## Provenance
DuckDB (MIT), `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory project `ext-duckdb` (full mode, 115,679 nodes / 595,569 edges, head==base==044a04a7 zero drift, generation 2026-08-23T11:00:58Z; parse_partial noise confined to data/*.csv fixtures, benchmark SQL, and C-API headers — none cited here except isolated declaration lines noted in capsules).

## Full view (memory graph)
Revalidate `ext-duckdb` before porting: run `index_status`, `check_index_coverage`, `search_graph`, `trace_path`, and `get_code_snippet`. Record the graph root, branch, commit, mode, node/edge counts, freshness, and any coverage caveats; source and direct tests decide shipped claims. BM25 search resolves this plane well (`ToUnifiedFormat`, `AdaptiveFilter`, `FillSwitch`, `TryExecuteDictionaryExpression`, `ResetFromCache`, `SetChildCardinality`, `DefaultSelect`, `SelectionVector.Incremental` all line-exact). check_index_coverage ×21 cited paths: clean (`no_recorded_issue`) for every .cpp seam file; three headers flagged partial at isolated declaration lines (unified_vector_format.hpp :29/:77-93, vector.hpp declaration lines, data_chunk.hpp declaration lines) — read directly from source, no behavioral claim rests on flagged lines; .test files are `not_tracked` by design (sqllogictest DSL). No C++ runner was executed in cron (no toolchain build): probes are deterministic greps against pinned source plus named upstream sqllogictest regressions.

## Boundaries
Adopt the pure contracts: unified-format element access, selection-vector arithmetic, alias/slice/dictionary discipline, fold-once constant execution, selection-threaded CASE/AND/OR evaluation, swap-trial adaptive ordering, dictionary-reuse gating, cache-slot chunk resets. Adapt host-specific integration: allocator plumbing, ValidityMask bit layout, sel_t width, UUID identity source, timing/RNG sources, FunctionStability vocabulary. Omit DuckDB product behavior: Variant shredding and FSST string dictionaries, the C++ template metaprogramming around physical types, serialization round-trip details, and the deprecated count-taking API shims.
