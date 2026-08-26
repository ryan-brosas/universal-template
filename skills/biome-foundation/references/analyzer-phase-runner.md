<!-- capsule-v2 -->
# Analyzer phase runner — how do phases, token pre-passes, and signal flushing interleave without a global sort?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a rule engine that runs visitors per phase must decide when suppression comments are parsed, when signals are flushed relative to traversal, and how a consumer stops early — what is the exact interleaving contract?

## The PhaseRunner seam
**Path/Symbol:** `crates/biome_analyze/src/lib.rs` — `Analyzer::run` (:140-247), `PhaseRunner::run_first_phase` (:289-324), `run_remaining_phases` (:328-351), `handle_token` (:356-394), `bump_line_index` (:566-582).
**Signature:** `pub fn run(self, mut ctx: AnalyzerContext<L>) -> Option<Break>` over `Analyzer<'analyzer, L, Matcher: QueryMatcher<L>, Break, Diag: Diagnostic + Clone + Send + Sync>`.
**Data Shape:** `phases: BTreeMap<Phases, Vec<Box<dyn Visitor<L>>>>` (Syntax=0 < Semantic=1); one fresh `BinaryHeap<SignalEntry>` per phase; ONE shared `line_index: &mut usize` across phases; ONE shared `Suppressions` across the whole run.

### Decisive source
```rust
// lib.rs:150-178 — the first phase to run owns suppression-comment parsing;
// later phases only read the cached line_suppressions:
let result = if index == 0 {
    runner.run_first_phase()
} else {
    runner.run_remaining_phases()
};
// run_first_phase: FIRST a full preorder_tokens pass calling handle_token
// (parses every comment via SuppressionParser, bumps line index), THEN
// suppressions.finalize() errors are emitted, and only then root.syntax().preorder()
// drives visitors. run_remaining_phases flushes after EVERY event instead.
```
```rust
// lib.rs:568-580 — line counting counts \n in leading trivia, the trimmed token,
// and trailing trivia; MultiLineComment and Skipped trivia ALSO bump the index.
for (index, _) in text.match_indices(['\n']) { ... }
if !did_match {
    self.suppressions.expand_range(range, *self.line_index);
}
```
**Flow:** enumerate BTreeMap phases → phase 0 = token pre-pass (suppressions) → finalize errors → node preorder × visitors → final `flush_matches(None)` → between phases each visitor's `finish(VisitorFinishContext)` runs OUTSIDE the runner because it needs `&mut ServiceBag` while the runner borrows services immutably (:184-192) → after ALL phases, unused range/line suppressions emit `suppressions/unused` diagnostics with an "another suppression comment suppresses" note when `already_suppressed` is set (:195-243). `flush_matches(cutoff)` pops entries whose start < cutoff, checks top-level category/rule keys, then range suppressions, then walks `overlapping_line_suppressions(&entry.text_range)` requiring `suppression.text_range.contains(start)`; instance suppressions lazily build `Option<FxHashSet<&Box<str>>>` and only count fully suppressed once every instance is removed (`is_exhaustive || instances.is_empty()`) (:442-496). Emission additionally requires `range_match(self.range, entry.text_range)` = filter intersect non-empty (:584-586). The generic `Break` parameter flows through `ControlFlow<B = Never>`: LSP consumers break at first diagnostic; `Option<Never>` is zero-sized so no-break runs compile the branch away (:948-974).
**Invariant:** signals discovered out of order still EMIT in start-offset order because the BinaryHeap's reversed Ord does the ordering and flush happens on the peeked minimum; suppression parsing happens exactly once (first phase), so a porter who re-parses comments in phase 1+ double-counts lines; visitor.finish mutates services only between phases, never mid-traversal.
**Probe:** `crates/biome_analyze/src/matcher.rs` tests :201-380 assert exact diagnostic ORDER ("Suppression errors first since we check suppressions before syntax rules") ending with suppressions/unused — this pins the first-phase-before-syntax-rules interleaving; `syntax.rs` test `syntax_visitor` :126-217 pins that Enter events alone reach the matcher for a two-literal tree.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "PhaseRunner handle_token flush_matches", limit: 10, fields: ["signature", "name", "file"] });
// PhaseRunner.handle_token lib.rs 356-394; PhaseRunner.flush_matches lib.rs 398-510 (line-exact)
```

## Verdict
Adopt the two-run shape (token pass for suppressions → node pass for rules), heap-ordered emission with cutoff flushing, finish-between-phases service mutation, and the Never-typed ControlFlow early-exit; adapt the number of phases and the comment syntax per language; omit the specific `is_allowed_before_suppressions` token-kind ladder unless porting Biome's top-level suppression placement rule. Coverage caveat: behavior pinned by matcher.rs order tests, not a dedicated integration suite.
